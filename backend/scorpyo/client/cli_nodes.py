import re
from dataclasses import dataclass, field

from scorpyo import definitions, innings, match
from scorpyo.event import EventType
from scorpyo.definitions.dismissal import DismissalType
from scorpyo.util import identity, try_int_convert


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
    is_node_0 = CommandLineNode(
        prompt="Batting team: ",
        payload_key="batting_team",
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


def file_input_reader(lines: list[str], print_output: bool):
    lines_iter = iter(lines)

    def _read(prompt_str):
        response = next(lines_iter)
        while response == "":
            response = next(lines_iter)
        if print_output:
            print(prompt_str, response)
        return response

    return _read
