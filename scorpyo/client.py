import abc
import json
from collections import deque
from contextlib import contextmanager
from io import IOBase
from typing import List, MutableSequence

from scorpyo.context import Context
from scorpyo.engine import MatchEngine, EngineState
from scorpyo.entity import EntityType
from scorpyo.events import EventType
from scorpyo.registrar import EntityRegistrar

"""
Ideally in future most entity data will be persisted server side but for
now the client can read in this info on startup each time and keep in memory
"""


class MatchClient:
    def __init__(self, engine: MatchEngine):
        self.engine: MatchEngine = engine
        self.registrar: EntityRegistrar = None
        self._sources: List[InputSource] = []
        self._pending_events = []

    def read(self):
        """loop through the input sources and instruct them to read new data"""
        for source in self._sources:
            source.read()

    def process(self):
        """do something with the new data"""
        for source in self._sources:
            for message in source.query():
                self.handle_message(message)

    def handle_message(self, message: dict):
        """interpret a message and send it to the engine, registrar or otherwise"""
        m_type = message.get("message_type")
        m_body = message.get("body")
        if not m_type or not m_body:
            raise ValueError(
                f"missing message type or body on incoming command" f" {message}"
            )
        funcs = {"entity": self.on_entity_message, "event": self.on_event_message}
        func = funcs.get(m_type)
        if not func:
            raise ValueError(f"invalid message type {m_type}")
        func(message["body"])

    def register_sources(self, sources: List["InputSource"]):
        """a list of sources, ordered according to which should be consumed first"""
        self._sources = sources

    def on_entity_message(self, message: dict):
        if not self.registrar:
            self.registrar = EntityRegistrar()
            Context.set_entity_registrar(self.registrar)
        e_type = message.get("entity_type")
        if not e_type:
            raise ValueError(f"entity message is missing entity type {message}")
        try:
            entity_type = EntityType[e_type.upper()]
        except KeyError:
            raise ValueError(f"entity message payload has an invalid type {e_type}")
        name = message.get("name")
        if not name:
            raise ValueError(f"entity message must have at least an entity name")
        if entity_type == EntityType.PLAYER:
            self.registrar.create_player(name)
        elif entity_type == EntityType.TEAM:
            self.registrar.create_team(name)

    def on_event_message(self, message: dict):
        """pass to the engine for processing and confirm the engine acked the message
        the client should know the internal protocol accepted by the engine and
        format messages accordingly. For now I will maintain this protocol distinctly
        between engine and client but if it grows, may need to move to protocol buff"""
        e_type = message.get("event_type")
        if not e_type:
            raise ValueError(f"no event type passed in event message")
        try:
            event_type = EventType[e_type.upper()]
        except KeyError:
            raise ValueError(f"event message payload has an invalid type {e_type}")
        event = message.get("body")
        if not event:
            raise ValueError(f"no body passed in event message")
        self.engine.handle_event(event_type, event)
        self._pending_events.append(event)

    @contextmanager
    def connect(self):
        for source in self._sources:
            source.connect()
        yield self
        for source in self._sources:
            source.close()


class InputSource(abc.ABC):
    """Mostly a wrapper around various sources of match messages (files, command line,
    web, database etc.)"""

    def __init__(self):
        self.is_connected = False
        self.message_buffer: deque = deque()

    def query(self):
        """clear the current cache"""
        while self.message_buffer:
            yield self.message_buffer.popleft()

    @abc.abstractmethod
    def connect(self):
        """open a connection to the underlying source"""
        pass

    @abc.abstractmethod
    def close(self):
        """close the connection to the underlying source"""
        pass

    @abc.abstractmethod
    def is_open(self):
        pass

    @abc.abstractmethod
    def read(self):
        """read from the source until the internal buffer is full and cache data that
        has yet to be processed upstream"""
        pass

    def has_data(self):
        return self.message_buffer


class FileSource(InputSource):

    URL = ""

    def __init__(self, url: str, reader=None):
        super().__init__()
        self.URL: str = url
        self.file_handler: IOBase = None
        self.reader = reader

    def connect(self):
        try:
            self.file_handler = open(self.URL, "r")
        except IOError:
            raise ConnectionError(f"error connecting to file source {self.URL}")

    def close(self):
        if self.is_open():
            self.file_handler.close()

    def read(self):
        self.reader(self.file_handler, self.message_buffer)

    def is_open(self):
        return not self.file_handler.closed


def json_reader(file_handler: IOBase, message_buffer: MutableSequence[str]):
    messages = json.loads(file_handler.read())
    for message in messages:
        message_buffer.append(message)


def plain_reader(file_handler: IOBase, message_buffer: MutableSequence[str]):
    # TODO pflanagan: if ever want to use key-value, then need this refactor so this
    # creates a dictionary from the source text
    for line in file_handler:
        message_buffer.append(line.strip())
