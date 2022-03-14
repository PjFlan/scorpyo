import abc
import json
import re
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from io import IOBase
from typing import MutableSequence

from scorpyo import static_data
from scorpyo.engine import MatchEngine
from scorpyo.entity import EntityType
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.static_data.dismissal import DismissalType
from scorpyo.util import load_config, identity, try_int_convert


# TODO pflanagan: this could probably be now moved to a sub-dir

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

    @property
    def is_open(self):
        return False

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


# beginning of CommandLineSource section


@dataclass
class CommandLineNode:
    prompt: str = ""
    payload_key: str = ""
    next_nodes: list = field(default_factory=list)
    is_list: bool = False
    post_process: callable = identity
    discrete: set = field(default_factory=set)
    is_entity: bool = False
    trigger_map: dict = field(default_factory=dict)
    can_trigger: set = field(default_factory=set)
    triggered_by: set = field(default_factory=set)


def add_dismissal_triggers(triggers: dict, dismissal_types: list[DismissalType]):
    # TODO pflanagan: could leverage a more functional approach below
    triggers["dismissal"] = ".*W$"
    triggers["fielder"] = "|".join(
        [f"^{dt.shortcode}$" for dt in dismissal_types if dt.needs_fielder]
    )
    triggers["batter"] = "|".join(
        [f"^{dt.shortcode}$" for dt in dismissal_types if not dt.batter_implied]
    )
    return triggers


def create_ms_nodes():
    # MatchStarted nodes
    match_type_options = ", ".join(
        [f"{mt.shortcode}={mt.name}" for mt in static_data.match.get_all_types()]
    )
    ms_away_team_node = CommandLineNode(
        prompt="Away Team: ",
        payload_key="away_team",
        is_entity=True,
    )
    ms_home_team_node = CommandLineNode(
        prompt="Home Team: ",
        payload_key="home_team",
        next_nodes=[ms_away_team_node],
        is_entity=True,
    )
    ms_match_type_node = CommandLineNode(
        prompt=f"Match type ({match_type_options}: ",
        payload_key="match_type",
        next_nodes=[ms_home_team_node],
        discrete=set(static_data.match.get_all_shortcodes()),
    )
    nodes = {
        node_name: node
        for node_name, node in locals().items()
        if isinstance(node, CommandLineNode)
    }
    return nodes


def create_rlu_nodes():
    # RegisterLineUp nodes
    rlu_lineup_node = CommandLineNode(
        prompt="Enter player names or IDs. Press 'F' to finish.\n",
        payload_key="lineup",
        is_list=True,
        is_entity=True,
    )
    rlu_team_node = CommandLineNode(
        prompt="Home (h) or away (a) lineup? ",
        payload_key="team",
        next_nodes=[rlu_lineup_node],
        post_process=lambda x: {"h": "home", "a": "away"}[x],
        discrete={"h", "a"},
    )
    nodes = {
        node_name: node
        for node_name, node in locals().items()
        if isinstance(node, CommandLineNode)
    }
    return nodes


def create_is_nodes():
    # InningsStarted nodes
    is_opening_bowler_node = CommandLineNode(
        prompt="Opening bowler: ",
        payload_key="opening_bowler",
        is_entity=True,
    )
    is_batting_team_node = CommandLineNode(
        prompt="Batting team: ",
        payload_key="batting_team",
        next_nodes=[is_opening_bowler_node],
        is_entity=True,
    )
    nodes = {
        node_name: node
        for node_name, node in locals().items()
        if isinstance(node, CommandLineNode)
    }
    return nodes


def create_bc_nodes():
    # BallCompleted nodes
    dismissal_types = static_data.dismissal.get_all_types()
    options = ", ".join([f"{dt.shortcode}={dt.name}" for dt in dismissal_types])
    dismissal_triggers = dict()
    add_dismissal_triggers(dismissal_triggers, dismissal_types)

    bc_batter_node = CommandLineNode(
        prompt="Batter: ",
        payload_key="dismissal.batter",
        is_entity=True,
        triggered_by={"batter"},
    )
    bc_fielder_node = CommandLineNode(
        prompt="Fielder: ",
        payload_key="dismissal.fielder",
        is_entity=True,
        triggered_by={"fielder"},
    )
    bc_dismissal_node = CommandLineNode(
        prompt=f"Dismissal type ({options}): ",
        payload_key="dismissal.type",
        next_nodes=[
            bc_fielder_node,
            bc_batter_node,
        ],
        trigger_map=dismissal_triggers,
        can_trigger={"fielder", "batter"},
        triggered_by={"dismissal"},
        discrete=set(static_data.dismissal.get_all_shortcodes()),
    )
    bc_score_node = CommandLineNode(
        prompt="Score text: ",
        payload_key="score_text",
        next_nodes=[bc_dismissal_node],
        trigger_map=dismissal_triggers,
        can_trigger={"dismissal"},
    )
    nodes = {
        node_name: node
        for node_name, node in locals().items()
        if isinstance(node, CommandLineNode)
    }
    return nodes


def create_cli_node_tree() -> dict:
    """returns a dict of the starting node for each event type. The remaining nodes
    can be determined by walking the node tree."""
    starting_node_map = {}

    ms_nodes = create_ms_nodes()
    starting_node_map[EventType.MATCH_STARTED] = ms_nodes["ms_match_type_node"]

    rlu_nodes = create_rlu_nodes()
    starting_node_map[EventType.REGISTER_LINE_UP] = rlu_nodes["rlu_team_node"]

    is_nodes = create_is_nodes()
    starting_node_map[EventType.INNINGS_STARTED] = is_nodes["is_batting_team_node"]

    bc_nodes = create_bc_nodes()
    starting_node_map[EventType.BALL_COMPLETED] = bc_nodes["bc_score_node"]

    return starting_node_map


def process_node_input(node, raw_value):
    if raw_value == "":
        print("cannot have empty input")
        return None
    processed_val = raw_value
    if node.discrete and processed_val not in node.discrete:
        print(f"value must be one of {node.discrete}")
        return None
    if node.is_entity:
        processed_val = try_int_convert(processed_val)
    return node.post_process(processed_val)


def check_triggers(node: CommandLineNode, value: str, active_triggers: set):
    if not node.can_trigger:
        return
    assert not node.is_list, "cannot use triggers with list input"
    assert isinstance(value, str), "cannot use non-string values with triggers"
    for trigger_key in node.can_trigger:
        assert node.trigger_map, "must specify a trigger map if node can trigger"
        trigger_pattern = node.trigger_map[trigger_key]
        if re.match(trigger_pattern, value):
            active_triggers.add(trigger_key)


def prepare_nested_payload(full_payload: dict, full_key: str) -> tuple[dict, str]:
    """takes the full payload and creates nested keys, as many as necessary,
    before returning a reference to the innermost nested dict and the name of the leaf
    key"""
    branches = full_key.split(".")
    payload_key = branches.pop(-1)  # the leaf key
    curr_branch = full_payload
    for parent_key in branches:
        if parent_key not in curr_branch:
            curr_branch[parent_key] = {}
        curr_branch = curr_branch[parent_key]
    return curr_branch, payload_key


class CommandLineSource(InputSource):
    def __init__(self, config, registrar: EntityRegistrar):
        super().__init__(registrar)
        self.config = config["COMMAND_LINE_SOURCE"]
        self.active = True
        self.event_nodes = create_cli_node_tree()

    @property
    def is_open(self):
        return self.active

    def connect(self):
        self.active = True
        self.on_connected()

    def on_connected(self):
        print(
            "\nWelcome to the scorpyo CLI. Type 'help' for a list of valid "
            "instructions, or 'quit' to exit."
        )

    def close(self):
        self.active = False

    def read(self):
        next_command = input("\n> ")
        if next_command == "help":
            self.show_help()
            return
        elif next_command == "quit":
            self.close()
            return
        elif next_command in {"player", "team"}:
            entity_type = EntityType[next_command.upper()]
            self.show_entities(entity_type)
            return
        else:
            try:
                event_type = EventType(next_command)
            except AttributeError:
                print("Not a valid command. Type 'help' for usage instructions.")
                return
        node_tree = deque()
        starting_node = self.event_nodes[event_type]
        node_tree.append(starting_node)
        body = {}
        active_triggers = set()
        while True:
            try:
                node = node_tree.pop()
            except IndexError:
                break
            if node.triggered_by and not node.triggered_by.issubset(active_triggers):
                continue
            input_value = process_node_input(node, input(node.prompt))
            if input_value is None:
                # inform the user of mistake and go again with the same node
                node_tree.append(node)
                continue
            if "." in node.payload_key:
                payload_section, payload_key = prepare_nested_payload(
                    body, node.payload_key
                )
            else:
                payload_section, payload_key = body, node.payload_key
            payload_value = input_value
            if node.is_list:
                payload_value = []
                while input_value != "F":
                    payload_value.append(input_value)
                    input_value = process_node_input(node, input("> "))
            payload_section[payload_key] = payload_value
            if len(node.next_nodes) > 0:
                node_tree.extend(node.next_nodes)
            check_triggers(node, payload_value, active_triggers)
        command = {"event": event_type.value, "body": body}
        self.command_buffer.append(command)

    def show_help(self):
        print(
            "Enter an event command using one of the following shortcodes ("
            "or type 'quit' to exit the client). To get all entities of a certain type "
            "and their unique ID, enter the entity type e.g. 'player' or 'team'."
        )
        for event in EventType:
            print(f"{event.value} = {event.name}")

    def show_entities(self, entity_type: EntityType):
        for ent in self.registrar.get_all_of_type(entity_type):
            print(f"{ent.unique_id} - {ent.name}")


def json_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    commands = json.loads(file_handler.read())
    for command in commands:
        command_buffer.append(command)


def plain_reader(file_handler: IOBase, command_buffer: MutableSequence[str]):
    for line in file_handler:
        command_buffer.append(line.strip())
