import abc
import json
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from io import IOBase
from typing import List, MutableSequence


from scorpyo.engine import MatchEngine
from scorpyo.entity import EntityType
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config, identity, try_int_convert

"""
Ideally in future most entity data will be persisted server side but for
now the client can read it on startup and keep in memory
"""


DEFAULT_CFG_DIR = "~/.config/scorpyo/scorpyo.cfg"


class MatchClient:
    def __init__(
        self, registrar: EntityRegistrar, engine: MatchEngine, config=DEFAULT_CFG_DIR
    ):
        self.registrar = registrar
        self.engine = engine
        self._pending_commands: deque = deque()
        self.engine_sequence = 0
        if isinstance(config, str):
            self.config = load_config(config)
        elif isinstance(config, dict):
            self.config = config
        self._source: InputSource = None
        self.register_source()

    def process(self):
        """do something with the new data"""
        while self._source.is_open:
            self._source.read()
            for command in self._source.query():
                self.handle_command(command)

    def handle_command(self, command: dict):
        """interpret a command and send it to the engine, registrar or otherwise"""
        if "body" not in command:
            raise ValueError(f"missing body on incoming command" f" {command}")
        self.on_event_command(command)

    def register_source(self):
        """a list of sources, ordered according to which should be consumed first"""
        source_name = self.config["CLIENT"]["source"]
        source_klass = {"file": FileSource, "command_line": CommandLineSource}[
            source_name
        ]
        self._source = source_klass(self.config, self.registrar)

    def on_event_command(self, command: dict):
        """pass to the engine for processing and confirm the engine acked the command
        the client should know the internal protocol accepted by the engine and
        format commands accordingly. For now I will maintain this protocol distinctly
        between engine and client but if it grows, may need to move to a protobuf"""
        e_type = command.get("event")
        if not e_type:
            raise ValueError(f"no event type passed in event command")
        try:
            # TODO: probably should be passing in the event id rather than raw string
            event_type = EventType(e_type)
        except KeyError:
            raise ValueError(f"event command payload has an invalid type {e_type}")
        event = command.get("body")
        if not event:
            raise ValueError(f"no data passed in event command")
        command["command_id"] = self.engine_sequence
        command["event"] = event_type
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
        self.engine.register_client(self)
        self._source.connect()
        yield self
        self._source.close()


class InputSource(abc.ABC):
    """Mostly a wrapper around various sources of match commands (files, command line,
    web, database etc.)"""

    def __init__(self, registrar: EntityRegistrar):
        self.registrar = registrar
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
    def read(self):
        """read from the source until the internal buffer is full and cache data that
        has yet to be processed upstream"""
        pass

    @property
    def has_data(self):
        return self.command_buffer


class FileSource(InputSource):
    def __init__(self, config: dict, registrar: EntityRegistrar):
        super().__init__(registrar)
        self.config = config["FILE_SOURCE"]
        self.url: str = self.config["url"]
        self.reader_func = {"json": json_reader, "plain": plain_reader}[
            self.config["reader"]
        ]
        self.file_handler = None

    @property
    def is_open(self):
        return not self.file_handler.closed

    def connect(self):
        try:
            self.file_handler = open(self.url, "r")
        except IOError:
            raise ConnectionError(f"error connecting to file source {self.url}")

    def close(self):
        if self.is_open:
            self.file_handler.close()

    def read(self):
        self.reader_func(self.file_handler, self.command_buffer)
        self.close()


@dataclass
class CommandLineNode:
    question: str
    key: str
    next_node: "CommandLineNode" = None
    is_list = False
    post_process: callable = identity
    trigger_key: int = 0
    discrete = []


ms_node_3 = CommandLineNode("Away Team: ", "away_team", post_process=try_int_convert)
ms_node_2 = CommandLineNode(
    "Home Team: ", "home_team", ms_node_3, post_process=try_int_convert
)
ms_node_1 = CommandLineNode("Match type: ", "match_type", ms_node_2)

rlu_node_2 = CommandLineNode("Enter player names or IDs. Press 'F' key to finish.\n",
                             "lineup", post_process=try_int_convert)
rlu_node_1 = CommandLineNode("Home (h) or away (a) team?", "team", rlu_node_2)

_NODES = {EventType.MATCH_STARTED: [ms_node_1, ms_node_2, ms_node_3],
          EventType.REGISTER_LINE_UP: [rlu_node_1, rlu_node_2]}


def handle_node_value(node, value):
    if node.discrete and value not in node.discrete:
        print(f"value must be one of {node.discrete}")
        return None
    return node.post_process(value)


class CommandLineSource(InputSource):
    def __init__(self, config, registrar: EntityRegistrar):
        super().__init__(registrar)
        self.active = True

    @property
    def is_open(self):
        return self.active

    def connect(self):
        self.active = True

    def close(self):
        self.active = False

    def read(self):
        """TODO pflanagan: query the DAG for the event type and exhaust all questions
        in order to obtain sufficient data to build a command"""
        next_command = input("\n > ")
        if next_command == "help":
            print(
                "Enter an event command using one of the following shortcodes ("
                "or type 'quit' to exit the client):"
            )
            for event in EventType:
                print(f"{event.value} = {event.name}")
                return
        elif next_command == "quit":
            self.close()
            return
        elif next_command == "players":
            for player in self.registrar.get_all_of_type(EntityType.PLAYER):
                print(f"{player.unique_id} - {player.name}")
            return
        elif next_command == "teams":
            for team in self.registrar.get_all_of_type(EntityType.TEAM):
                print(f"{team.unique_id} - {team.name}")
            return
        else:
            try:
                event_type = EventType(next_command)
            except AttributeError:
                print("Not a valid command. Type 'help' for usage instructions.")
                return
        nodes = _NODES[event_type]
        node = nodes[0]
        body = {}
        while node:
            key = node.key
            value = handle_node_value(input(node.question))
            if not value:
                continue
            if node.is_list:
                value_list = []
                while value != "F":
                    value_list.append(value)
                    value = handle_node_value(input(node.question))
                body[key] = value_list
            else:
                body[key] = value
            node = node.next_node
        command = {"event": event_type.value, "body": body}
        self.command_buffer.append(command)


def json_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    commands = json.loads(file_handler.read())
    for command in commands:
        command_buffer.append(command)


def plain_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    # TODO pflanagan: if ever want to use key-value, then need this refactor so this
    # creates a dictionary from the source text
    for line in file_handler:
        command_buffer.append(line.strip())
