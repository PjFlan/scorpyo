import abc
import json
import os
import re
from collections import deque
from dataclasses import dataclass, field

from scorpyo import definitions, innings, match
from scorpyo.client.reader import json_reader, plain_reader
from scorpyo.entity import EntityType
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.definitions.dismissal import DismissalType
from scorpyo.util import identity, try_int_convert


class ClientHandler(abc.ABC):
    """Mostly a wrapper around various sources of match commands (files, command line,
    web, database etc.)"""

    def __init__(self, config: dict, registrar: EntityRegistrar):
        try:
            self.root_dir = config["CLIENT"]["root_dir"]
        except KeyError:
            self.root_dir = "../"
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

    @abc.abstractmethod
    def on_message(self, message: dict):
        pass

    @property
    def has_data(self):
        return self.command_buffer


class FileHandler(ClientHandler):
    def __init__(self, config: dict, registrar: EntityRegistrar):
        super().__init__(config, registrar)
        self.config = config["FILE_HANDLER"]
        self.url: str = os.path.join(self.root_dir, self.config["url"])
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

    def on_message(self, message: dict):
        print(json.dumps(message, indent=4))


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


def create_nodes():
    # MatchStarted nodes
    match_type_options = ", ".join(
        [f"{mt.shortcode}={mt.name}" for mt in definitions.match.get_all_types()]
    )
    ms_node_2 = CommandLineNode(
        prompt="Away Team: ",
        payload_key="away_team",
        is_entity=True,
    )
    ms_node_1 = CommandLineNode(
        prompt="Home Team: ",
        payload_key="home_team",
        next_nodes=[ms_node_2],
        is_entity=True,
    )
    ms_node_0 = CommandLineNode(
        prompt=f"Match type ({match_type_options}): ",
        payload_key="match_type",
        next_nodes=[ms_node_1],
        discrete=set(definitions.match.get_all_shortcodes()),
    )

    # RegisterLineUp nodes
    rlu_node_1 = CommandLineNode(
        prompt="Enter player names or IDs. Press 'F' to finish.",
        payload_key="lineup",
        is_list=True,
        is_entity=True,
    )
    rlu_node_0 = CommandLineNode(
        prompt="Home (h) or away (a) lineup? ",
        payload_key="team",
        next_nodes=[rlu_node_1],
        post_process=lambda x: {"h": "home", "a": "away"}[x],
        discrete={"h", "a"},
    )

    # InningsStarted nodes
    is_node_1 = CommandLineNode(
        prompt="Opening bowler: ",
        payload_key="opening_bowler",
        is_entity=True,
    )
    is_node_0 = CommandLineNode(
        prompt="Batting team: ",
        payload_key="batting_team",
        next_nodes=[is_node_1],
        is_entity=True,
    )

    # BallCompleted nodes
    dismissal_types = definitions.dismissal.get_all_types()
    options = ", ".join([f"{dt.shortcode}={dt.name}" for dt in dismissal_types])
    dismissal_triggers = dict()
    add_dismissal_triggers(dismissal_triggers, dismissal_types)

    bc_node_3 = CommandLineNode(
        prompt="Batter: ",
        payload_key="dismissal.batter",
        is_entity=True,
        triggered_by={"batter"},
    )
    bc_node_2 = CommandLineNode(
        prompt="Fielder: ",
        payload_key="dismissal.fielder",
        is_entity=True,
        triggered_by={"fielder"},
    )
    bc_node_1 = CommandLineNode(
        prompt=f"Dismissal type ({options}): ",
        payload_key="dismissal.type",
        next_nodes=[
            bc_node_2,
            bc_node_3,
        ],
        trigger_map=dismissal_triggers,
        can_trigger={"fielder", "batter"},
        triggered_by={"dismissal"},
        discrete=set(definitions.dismissal.get_all_shortcodes()),
    )
    bc_node_0 = CommandLineNode(
        prompt="Score text: ",
        payload_key="score_text",
        next_nodes=[bc_node_1],
        trigger_map=dismissal_triggers,
        can_trigger={"dismissal"},
    )

    # OverStarted nodes
    os_node_0 = CommandLineNode(
        prompt="Bowler: ",
        payload_key="bowler",
        is_entity=True,
    )

    # InningsCompleted nodes
    innings_complete_options = ", ".join(
        [f"{state.value}={state.name}" for state in innings.InningsState]
    )
    ic_node_0 = CommandLineNode(
        prompt=f"Reason ({innings_complete_options}): ",
        payload_key="reason",
        discrete=set(state.value for state in innings.InningsState),
    )

    # MatchCompleted nodes
    match_complete_options = ", ".join(
        [f"{state.value}={state.name}" for state in match.MatchState]
    )
    mc_node_0 = CommandLineNode(
        prompt=f"Reason ({match_complete_options}): ",
        payload_key="reason",
        discrete=set(state.value for state in match.MatchState),
    )

    # BatterInningsStarted nodes
    bis_node_1 = CommandLineNode()
    bis_node_0 = CommandLineNode(
        prompt="Batter: ",
        payload_key="batter",
        is_entity=True,
    )

    # BatterInningsCompleted nodes
    bic_options = ", ".join(
        [f"{state.value}={state.name}" for state in innings.BatterInningsState]
    )
    bic_node_1 = CommandLineNode(
        prompt=f"Reason ({bic_options}): ",
        payload_key="reason",
        discrete=set(state.value for state in innings.BatterInningsState),
    )
    bic_node_0 = CommandLineNode(
        prompt="Batter: ", payload_key="batter", is_entity=True, next_nodes=[bic_node_1]
    )

    nodes = {
        node_name: node
        for node_name, node in locals().items()
        if isinstance(node, CommandLineNode)
    }
    return nodes


def get_starting_event_nodes(
    all_nodes: dict[str, CommandLineNode]
) -> dict[EventType, CommandLineNode]:
    root_nodes_map = {}
    for event_type in EventType:
        search_str = f"{event_type.value}_node_0"
        try:
            starting_node = all_nodes[search_str]
        except KeyError:
            # some nodes do not need further input
            continue
        root_nodes_map[event_type] = starting_node
    return root_nodes_map


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
    """see if the input value for a given node can activate any triggers"""
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


def file_input_reader(lines: list[str]):
    lines_iter = iter(lines)

    def _read(prompt_str):
        response = next(lines_iter)
        while response == "":
            response = next(lines_iter)
        print(prompt_str, response)
        return response

    return _read


class CommandLineHandler(ClientHandler):
    def __init__(self, config, registrar: EntityRegistrar):
        super().__init__(config, registrar)
        self.config = config["COMMAND_LINE_HANDLER"]
        self.active = True
        self.event_nodes = create_nodes()
        self.starting_nodes_map = get_starting_event_nodes(self.event_nodes)
        self.input_reader = input

    @property
    def is_open(self):
        return self.active

    def connect(self):
        self.active = True
        self.on_connected()

    def on_connected(self):
        if self.config["use_file"]:
            file_source = os.path.join(self.root_dir, self.config["input_source"])
            with open(file_source) as fh:
                lines = [x.strip() for x in fh]
            self.input_reader = file_input_reader(lines)
        print(
            "\nWelcome to the scorpyo CLI. Type 'help' for a list of valid "
            "instructions, or 'quit' to exit."
        )

    def close(self):
        self.active = False

    def read(self):
        next_command = self.input_reader("\n> ")
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
        body = {}
        starting_node = self.starting_nodes_map.get(event_type)
        if starting_node:
            node_tree.append(starting_node)
        active_triggers = set()
        while True:
            try:
                node = node_tree.pop()
            except IndexError:
                break
            if node.triggered_by and not node.triggered_by.issubset(active_triggers):
                continue
            if node.is_list:
                input_value = []
                print(node.prompt)
                raw_val = self.input_reader("> ")
                while raw_val != "F":
                    value = process_node_input(node, raw_val)
                    input_value.append(value)
                    raw_val = self.input_reader("> ")
            else:
                input_value = process_node_input(node, self.input_reader(node.prompt))
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
            payload_section[payload_key] = payload_value
            if len(node.next_nodes) > 0:
                node_tree.extend(node.next_nodes)
            check_triggers(node, payload_value, active_triggers)
        command = {"event": event_type.value, "body": body}
        self.command_buffer.append(command)

    def on_message(self, message: dict):
        print(json.dumps(message, indent=4))

    def show_help(self):
        print(
            "Enter an event command using one of the following shortcodes ("
            "or type 'quit' to exit the client). To get all entities of a certain type "
            "and their unique ID, enter the entity type e.g. 'player' or 'team'."
        )
        for event in EventType:
            print(f"{event.value}={event.name}")

    def show_entities(self, entity_type: EntityType):
        for ent in self.registrar.get_all_of_type(entity_type):
            print(f"{ent.unique_id} - {ent.name}")
