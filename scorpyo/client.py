import abc
import json
from collections import deque
from contextlib import contextmanager
from io import IOBase
from typing import List, MutableSequence

import configparser

from scorpyo.engine import MatchEngine
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar

"""
Ideally in future most entity data will be persisted server side but for
now the client can read it on startup and keep in memory
"""


DEFAULT_CFG_DIR = "~/.config/scorpyo/scorpyo.cfg"


def load_config(config_file: str):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


class MatchClient:
    def __init__(self, config_file=""):
        self.registrar: EntityRegistrar = EntityRegistrar()
        self.engine = MatchEngine(self.registrar)
        self._sources: List[InputSource] = []
        self._pending_commands: deque = deque()
        self.engine_sequence = 0
        if not config_file:
            config_file = DEFAULT_CFG_DIR
        self.config = load_config(config_file)
        self.load_entities()

    def read(self):
        """loop through the input sources and trigger them to read new data"""
        for source in self._sources:
            source.read()

    def process(self):
        """do something with the new data"""
        for source in self._sources:
            for command in source.query():
                self.handle_command(command)

    def assign_engine(self, engine: MatchEngine):
        self.engine = engine
        self.engine.register_client(self)

    def handle_command(self, command: dict):
        """interpret a command and send it to the engine, registrar or otherwise"""
        m_type = command.get("command_type")
        m_body = command.get("body")
        if not m_type or not m_body:
            raise ValueError(
                f"missing command type or body on incoming command" f" {command}"
            )
        funcs = {"entity": self.on_entity_command, "event": self.on_event_command}
        func = funcs.get(m_type)
        if not func:
            raise ValueError(f"invalid command type {m_type}")
        func(command["body"])

    def register_sources(self, sources: List["InputSource"]):
        """a list of sources, ordered according to which should be consumed first"""
        self._sources = sources

    def load_entities(self):
        entities_config = self.config["ENTITIES"]
        self.registrar.load_entities(entities_config)

    def on_event_command(self, command: dict):
        """pass to the engine for processing and confirm the engine acked the command
        the client should know the internal protocol accepted by the engine and
        format commands accordingly. For now I will maintain this protocol distinctly
        between engine and client but if it grows, may need to move to a protobuf"""
        e_type = command.get("event_type")
        if not e_type:
            raise ValueError(f"no event type passed in event command")
        try:
            # TODO: probably should be passing in the event id rather than raw string
            event_type = EventType[e_type.upper()]
        except KeyError:
            raise ValueError(f"event command payload has an invalid type {e_type}")
        event = command.get("body")
        if not event:
            raise ValueError(f"no data passed in event command")
        command["command_id"] = self.engine_sequence
        command["event_type"] = event_type
        self.engine_sequence += 1
        self._pending_commands.append(command)
        self.engine.on_event(command)

    def on_message(self, message: dict):
        message_id = message.get("message_id")
        if message_id is None:
            raise ValueError(f"received message from engine with know id {message}")
        if len(self._pending_commands) == 0:
            raise ValueError(f"received message from engine without pending commands")
        oldest_command = self._pending_commands.popleft()
        command_id = oldest_command["command_id"]
        assert message_id == command_id, (
            f"message_id does not match command_id of "
            "oldest pending command {message_id} != {command_id}"
        )
        print(json.dumps(message, indent=4))

    @contextmanager
    def connect(self):
        for source in self._sources:
            source.connect()
        yield self
        for source in self._sources:
            source.close()


class InputSource(abc.ABC):
    """Mostly a wrapper around various sources of match commands (files, command line,
    web, database etc.)"""

    def __init__(self):
        self.is_connected = False
        self.command_buffer: deque = deque()

    def query(self):
        """clear the current cache"""
        while self.command_buffer:
            yield self.command_buffer.popleft()

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
        return self.command_buffer


class FileSource(InputSource):

    URL = ""

    def __init__(self, url: str, reader=None):
        super().__init__()
        self.URL: str = url
        self.file_handler = None
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
        self.reader(self.file_handler, self.command_buffer)

    def is_open(self):
        return not self.file_handler.closed


class CommandLineSource(InputSource):
    def __init__(self):
        super().__init__()
        self.active = True

    def connect(self):
        self.active = True

    def close(self):
        self.active = False

    def is_open(self):
        return self.active

    def read(self):
        """TODO pflanagan: query the DAG for the event type and exhaust all questions
        in order to obtain sufficient data to build a command"""
        pass


def json_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    commands = json.loads(file_handler.read())
    for command in commands:
        command_buffer.append(command)


def plain_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    # TODO pflanagan: if ever want to use key-value, then need this refactor so this
    # creates a dictionary from the source text
    for line in file_handler:
        command_buffer.append(line.strip())
