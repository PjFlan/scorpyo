import abc
import queue
from io import IOBase
from typing import List

from scorpyo.context import Context
from scorpyo.engine import MatchEngine, EngineState
from scorpyo.entity import EntityType
from scorpyo.registrar import EntityRegistrar


# Ideally in future most entity data will be persisted server side but for
# now the client can read in this info on startup each time and keep in memory
class MatchClient:
    def __init__(self, engine: MatchEngine):
        self.engine: MatchEngine = engine
        self.registrar: EntityRegistrar = None
        self.sources: List[InputSource] = []

    def read(self):
        # go to various input sources and query for new data
        # there should be a hierarchy of which gets read first (e.g. entity before
        # events) but should also be away for our sources to forward new data
        pass

    def handle_message(self, message: dict):
        # interpret message and send it to the engine, registrar or otherwise
        m_type = message["message_type"]
        m_body = message["body"]
        if not m_type or not m_body:
            raise ValueError(
                f"missing message type or body on incoming command" f" {message}"
            )
        func = {"entity": self.on_entity_message, "event": self.on_event_message}[
            m_type
        ]
        func(message)

    def register_source(self, source: "InputSource"):
        self.sources.append(source)

    def on_entity_message(self, payload: dict):
        if not self.registrar:
            self.registrar = EntityRegistrar()
            Context.set_entity_registrar(self.registrar)
        e_type = payload.get("entity_type")
        if not e_type:
            raise ValueError(f"entity message is missing entity type {payload}")
        try:
            entity_type = EntityType[e_type]
        except KeyError:
            raise ValueError(f"entity message payload has an invalid type {e_type}")
        if entity_type == EntityType.PLAYER:
            self.registrar.create_player(payload["name"])
        elif entity_type == EntityType.TEAM:
            self.registrar.create_team(payload["name"])

    def on_event_message(self, payload: dict):
        # pass to the engine for processing and confirm the engine acked the message
        assert (
            self.engine.state == EngineState.RUNNNING
        ), "engine is not running, cannot accept new messages"
        pass

    @property
    def is_match_ready(self):
        # do we have appropriate entity data to begin a match with
        # or should we continue reading for more
        # if we try to interpret an event message while this is still false
        # then we have an issue
        return False

    def __enter__(self):
        pass

    def __exit__(self):
        for source in self.sources:
            source.close()


class InputSource(abc.ABC):

    # Mostly a wrapper around various sources of match messages (files, command line,
    # web etc.)
    def __init__(self):
        self.messages = queue.Queue()
        self.is_connected = False

    def query(self):
        # do we have new data available to pass to the reader
        if not self.messages.empty():
            return self.messages.get()
        return None

    @abc.abstractmethod
    def connect(self):
        # open a connection to the underlying stream
        pass

    @abc.abstractmethod
    def close(self):
        # close the connection to the underlying
        pass

    @abc.abstractmethod
    def has_data(self):
        pass

    @abc.abstractmethod
    def read(self):
        # read from the stream until the internal buffer is full and cache data that
        # has yet to be read upstream
        pass


class FileSource(InputSource):

    URL = ""

    def __init__(self, url: str):
        super().__init__()
        self.URL: str = url
        self.file_handler: IOBase = None
        self.cache: queue.Queue = queue.Queue()

    def connect(self):
        try:
            self.file_handler = open(self.URL)
        except IOError:
            raise ConnectionError(f"error connecting to file source {self.URL}")

    def close(self):
        if not self.file_handler.closed:
            self.file_handler.close()

    def has_data(self):
        return not self.cache.empty()

    def read(self):
        for line in self.file_handler.readlines():
            self.cache.put(line)
