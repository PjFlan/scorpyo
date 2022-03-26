import builtins
import json
from io import StringIO
from typing import List
from unittest import TestCase

import pytest

from scorpyo import client, static_data, innings, match
from scorpyo.client import (
    MatchClient,
    FileSource,
    json_reader,
    CommandLineSource,
    CommandLineNode,
    process_node_input,
)
from scorpyo.engine import MatchEngine
from scorpyo.entity import EntityType
from scorpyo.registrar import EntityRegistrar
from tests.common import TEST_CONFIG_PATH
from tests.resources import HOME_PLAYERS, AWAY_PLAYERS, HOME_TEAM, AWAY_TEAM

LINES = ["test line 1", "test line 2", "test line 3"]
TEST_JSON = '[{"a": "test line 1"}, {"b": "test line 2"}, {"c": "test line 3"}]'


class MockStringIO(StringIO):
    """a wrapper around StringIO to write onto newlines and flip buffer"""

    pos = 0

    def __init__(self):
        super().__init__()

    def write_lines(self, lines: List[str]):
        new_lines = "\n".join(lines)
        bytes_written = super().write(new_lines)
        self.seek(self.pos)
        self.pos += bytes_written
        return bytes_written

    def write(self, line: str):
        bytes_written = super().write(line)
        self.seek(self.pos)
        self.pos += bytes_written
        return bytes_written


@pytest.fixture
def mock_file():
    return MockStringIO()


@pytest.fixture
def mock_client(mock_engine: MatchEngine, registrar: EntityRegistrar):
    my_client = MatchClient(registrar, mock_engine, TEST_CONFIG_PATH)
    return my_client


def test_client_setup(mock_engine: MatchEngine, mock_file, registrar, monkeypatch):
    my_client = MatchClient(registrar, mock_engine, TEST_CONFIG_PATH)
    monkeypatch.setattr(builtins, "open", lambda x: mock_file)
    with my_client.connect() as _client:
        assert _client._source is not None
        assert _client._source.is_open
    assert not my_client._source.is_open


def test_file_source_plain_reader(registrar, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {"FILE_SOURCE": {"url": "/path/to/url", "reader": "plain"}}
    file_source = FileSource(config, registrar)
    file_source.connect()
    mock_file.write_lines(LINES[0:2])
    file_source.read()
    assert len(file_source.command_buffer) == 2


def test_file_source_json_reader(registrar, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {"FILE_SOURCE": {"url": "/path/to/url", "reader": "json"}}
    file_source = FileSource(config, registrar)
    file_source.connect()
    mock_file.write(TEST_JSON)
    file_source.read()
    assert len(file_source.command_buffer) == 3
    read_lines = []
    for line in file_source.query():
        read_lines.append(line)
    assert read_lines == json.loads(TEST_JSON)
    file_source.close()


def test_client_plain_reader(mock_file, mocker, registrar, mock_engine, monkeypatch):
    config = {
        "CLIENT": {"source": "file"},
        "FILE_SOURCE": {"url": "/path/to/url", "reader": "plain"},
    }
    mock_client = MatchClient(registrar, mock_engine, config)
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    mock_file.write_lines(LINES)
    patched = mocker.patch.object(MatchClient, "handle_command")
    with mock_client.connect() as client:
        client.process()
    assert patched.call_count == 3
    assert not mock_client._source.has_data


def test_client_json_reader(mock_file, mocker, registrar, mock_engine, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {
        "CLIENT": {"source": "file"},
        "FILE_SOURCE": {"url": "/path/to/url", "reader": "json"},
    }
    mock_client = MatchClient(registrar, mock_engine, config)
    mock_client._source.reader = json_reader
    mock_file.write(TEST_JSON)
    patched = mocker.patch.object(MatchClient, "handle_command")
    with mock_client.connect() as client:
        client.process()
    assert patched.call_count == 3
    assert not mock_client._source.has_data


def test_event_command_handler(mock_client, mocker):
    event_patch = mocker.patch.object(MatchClient, "on_event_command")
    test_command = {"event": "null", "body": {"dummy2": "test"}}
    mock_client.handle_command(test_command)
    assert event_patch.called_with(test_command["body"])


def test_command_missing_body(mock_client):
    with pytest.raises(ValueError):
        bad_command = {"event": "null"}
        mock_client.handle_command(bad_command)


def test_event_command(mock_client, mocker):
    handler_patch = mocker.patch.object(MatchEngine, "handle_event")
    event = {"event": "ms", "body": {"noop": "noop"}}
    mock_client.on_event_command(event)
    assert handler_patch.called_with({"noop": "noop"})


@pytest.mark.parametrize(
    "node,user_input,output",
    [
        (CommandLineNode(is_entity=True), "1", 1),
        (CommandLineNode(discrete=["a", "b"]), "c", None),
    ],
)
def test_node_handler(node, user_input, output):
    processed = process_node_input(node, user_input)
    assert processed == output


@pytest.mark.parametrize(
    "method,user_input",
    [
        ("show_help", "help"),
        ("close", "quit"),
        ("show_entities", "team"),
        ("show_entities", "player"),
    ],
)
def test_command_line_source(registrar, mocker, method, user_input):
    source = CommandLineSource({"COMMAND_LINE_SOURCE": {}}, registrar)
    patcher = mocker.patch.object(CommandLineSource, method)
    mock_input = mocker.Mock()
    mock_input.side_effect = [user_input]
    mocker.patch("builtins.input", mock_input)
    source.read()
    assert patcher.called


@pytest.mark.parametrize(
    "user_inputs,expected_command",
    [
        # MatchStarted
        (
            ["ms", "T20", HOME_TEAM, AWAY_TEAM],
            {"match_type": "T20", "home_team": HOME_TEAM, "away_team": AWAY_TEAM},
        ),
        # RegisterLineUp
        (["rlu", "h"] + HOME_PLAYERS + ["F"], {"team": "home", "lineup": HOME_PLAYERS}),
        # InningsStarted
        (
            ["is", HOME_TEAM, AWAY_PLAYERS[-1]],
            {"batting_team": HOME_TEAM, "opening_bowler": AWAY_PLAYERS[-1]},
        ),
        # BallCompleted
        (["bc", "1"], {"score_text": "1"}),
        (["bc", "1W", "b"], {"score_text": "1W", "dismissal": {"type": "b"}}),
        (
            ["bc", "1W", "ct", 0],
            {"score_text": "1W", "dismissal": {"type": "ct", "fielder": 0}},
        ),
        (
            ["bc", "W", "ro", 12, 0],
            {
                "score_text": "W",
                "dismissal": {"type": "ro", "fielder": 0, "batter": 12},
            },
        ),
        # OverStarted
        (["os", AWAY_PLAYERS[-1]], {"bowler": AWAY_PLAYERS[-1]}),
        # OverCompleted
        (["oc"], {}),
        # InningsCompleted
        (
            ["ic", innings.InningsState.ALL_OUT.value],
            {"reason": innings.InningsState.ALL_OUT.value},
        ),
        # MatchCompleted
        (
            ["mc", match.MatchState.COMPLETED.value],
            {"reason": match.MatchState.COMPLETED.value},
        ),
        # BatterInningsStarted
        (["bis", HOME_PLAYERS[3]], {"batter": HOME_PLAYERS[3]}),
        # BatterInningsCompleted
        (
            ["bic", HOME_PLAYERS[1], innings.BatterInningsState.DISMISSED.value],
            {
                "batter": HOME_PLAYERS[1],
                "reason": innings.BatterInningsState.DISMISSED.value,
            },
        ),
    ],
)
def test_command_line_source(
    registrar, mocker, user_inputs, expected_command, monkeypatch
):
    source = CommandLineSource({"COMMAND_LINE_SOURCE": {}}, registrar)
    mock_input = mocker.Mock()
    mock_input.side_effect = user_inputs
    monkeypatch.setattr(source, "input_reader", mock_input)
    source.read()
    assert len(source.command_buffer) == 1
    command = source.command_buffer[0]
    TestCase().assertDictEqual(expected_command, command["body"])


def test_nested_payload():
    full_payload = {"dummy_key": "dummy_value"}
    full_key = "dismissal.batter"
    inner_payload, inner_key = client.prepare_nested_payload(full_payload, full_key)
    assert inner_payload == {}
    assert inner_key == "batter"
    assert full_payload == {"dummy_key": "dummy_value", "dismissal": {}}


def test_dismissal_triggers():
    triggers = dict()
    dismissal_types = static_data.dismissal.get_all_types()
    client.add_dismissal_triggers(triggers, dismissal_types)
    assert set(triggers.keys()) == set(["dismissal", "fielder", "batter"])
    assert triggers["batter"] == "^ro$|^hb$|^of$"
    assert triggers["fielder"] == "^ct$|^ro$"
    assert triggers["dismissal"] == ".*W$"


@pytest.mark.parametrize(
    "user_input,node_name,expected_triggers",
    [
        ("1W", "bc_node_0", {"dismissal"}),
        ("1lb", "bc_node_0", set()),
        ("ct", "bc_node_1", {"fielder"}),
        ("ro", "bc_node_1", {"batter", "fielder"}),
        ("b", "bc_node_1", set()),
    ],
)
def test_ball_completed_dismissal_triggers(user_input, node_name, expected_triggers):
    active_triggers = set()
    nodes = client.create_nodes()
    node = nodes[node_name]
    client.check_triggers(node, user_input, active_triggers)
    assert active_triggers == expected_triggers
