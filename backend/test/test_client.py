import builtins
import json
from io import StringIO
from typing import List
from unittest import TestCase

import pytest

from scorpyo import definitions, innings, match
from scorpyo.client.cli_nodes import CommandLineNode, add_dismissal_triggers
from scorpyo.client.client import EngineClient
from scorpyo.client.reader import json_reader
from scorpyo.client.handler import (
    FileHandler,
    process_node_input,
    CommandLineHandler,
    prepare_nested_payload,
    create_nodes,
    check_triggers,
    WSHandler,
)
from scorpyo.engine import MatchEngine
from scorpyo.error import EngineError, ClientError, RejectReason
from scorpyo.registrar import EntityRegistrar
from test.common import TEST_CONFIG_PATH
from test.resources import HOME_PLAYERS, AWAY_PLAYERS, HOME_TEAM, AWAY_TEAM

LINES = ["test line 1", "test line 2", "test line 3"]
TEST_JSON = '[{"a": "test line 1"}, {"b": "test line 2"}, {"c": "test line 3"}]'


class MockStringIO(StringIO):
    """a wrapper around StringIO to write onto newlines and flip the buffer"""

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
def mock_client(mock_engine: MatchEngine, registrar: EntityRegistrar, monkeypatch):
    config = {
        "CLIENT": {"handler": "file"},
        "FILE_HANDLER": {"url": "/path/to/url", "reader": "json"},
    }
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    my_client = EngineClient(registrar, mock_engine, config)
    return my_client


def test_client_setup(mock_engine: MatchEngine, mock_file, registrar, monkeypatch):
    config = {
        "CLIENT": {"handler": "file"},
        "FILE_HANDLER": {"url": "/path/to/url", "reader": "json"},
    }
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    my_client = EngineClient(registrar, mock_engine, config)
    with my_client.connect() as _client:
        assert _client._handler is not None
        assert _client._handler.is_open
    assert not my_client._handler.is_open


def test_file_source_plain_reader(registrar, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {"FILE_HANDLER": {"url": "/path/to/url", "reader": "plain"}}
    file_source = FileHandler(config, registrar)
    file_source.connect()
    mock_file.write_lines(LINES[0:2])
    file_source.read()
    assert len(file_source.command_buffer) == 2


def test_file_source_json_reader(registrar, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {"FILE_HANDLER": {"url": "/path/to/url", "reader": "json"}}
    file_source = FileHandler(config, registrar)
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
        "CLIENT": {"handler": "file", "power_save_timeout": "0"},
        "FILE_HANDLER": {"url": "/path/to/url", "reader": "plain"},
    }
    mock_client = EngineClient(registrar, mock_engine, config)
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    mock_file.write_lines(LINES)
    patched = mocker.patch.object(EngineClient, "handle_command")
    with mock_client.connect() as _client:
        _client.process()
    assert patched.call_count == 3
    assert not mock_client._handler.has_data


def test_client_json_reader(mock_file, mocker, registrar, mock_engine, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {
        "CLIENT": {"handler": "file", "power_save_timeout": "0"},
        "FILE_HANDLER": {"url": "/path/to/url", "reader": "json"},
    }
    mock_client = EngineClient(registrar, mock_engine, config)
    mock_client._handler.reader = json_reader
    mock_file.write(TEST_JSON)
    patched = mocker.patch.object(EngineClient, "handle_command")
    with mock_client.connect() as _client:
        _client.process()
    assert patched.call_count == 3
    assert not mock_client._handler.has_data


def test_event_command_handler(mock_client, mocker):
    event_patch = mocker.patch.object(EngineClient, "on_event_command")
    test_command = {"event": "null", "body": {"dummy2": "test"}}
    mock_client.handle_command(test_command)
    event_patch.assert_called_with(test_command)


def test_command_missing_body_reject(mock_client, monkeypatch, mocker):
    mocker.patch.object(FileHandler, "on_message")
    bad_command = {"event": "null"}
    mock_client.handle_command(bad_command)
    args, kwargs = FileHandler.on_message.call_args
    assert args[0]["reject_reason"] == RejectReason.BAD_COMMAND.value


@pytest.mark.parametrize(
    "node,user_input,output",
    [
        (CommandLineNode(is_entity=True), "1", 1),
        (CommandLineNode(discrete={"a", "b"}), "c", None),
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
    source = CommandLineHandler({"COMMAND_LINE_HANDLER": {}}, registrar)
    patcher = mocker.patch.object(CommandLineHandler, method)
    mock_input = mocker.Mock()
    mock_input.side_effect = [user_input]
    mocker.patch("builtins.input", mock_input)
    source.read()
    patcher.assert_called()


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
            {"batting_team": HOME_TEAM},
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
    source = CommandLineHandler({"COMMAND_LINE_HANDLER": {}}, registrar)
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
    inner_payload, inner_key = prepare_nested_payload(full_payload, full_key)
    assert inner_payload == {}
    assert inner_key == "batter"
    assert full_payload == {"dummy_key": "dummy_value", "dismissal": {}}


def test_dismissal_triggers():
    triggers = dict()
    dismissal_types = definitions.dismissal.get_all_types()
    add_dismissal_triggers(triggers, dismissal_types)
    assert set(triggers.keys()) == {"dismissal", "fielder", "batter"}
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
    nodes = create_nodes()
    node = nodes[node_name]
    check_triggers(node, user_input, active_triggers)
    assert active_triggers == expected_triggers


def test_ws_handler_connect(mock_file, mocker, registrar, mock_engine, monkeypatch):
    config = {
        "CLIENT": {"handler": "ws"},
        "WEB_SOCKET_HANDLER": {"host": "127.0.0.1", "port": "13254"},
    }
    mock_server = mocker.Mock()
    monkeypatch.setattr(WSHandler, "_setup_server", lambda *x, **y: mock_server)
    run_patcher = mocker.patch.object(mock_server, "run_forever")
    ws_handler = WSHandler(config, registrar)
    assert ws_handler._server is None
    ws_handler.connect()
    assert ws_handler._server is not None
    assert ws_handler.is_open()
    run_patcher.assert_called_once()


def test_ws_handler_close(mock_file, mocker, registrar, mock_engine, monkeypatch):
    config = {
        "CLIENT": {"handler": "ws"},
        "WEB_SOCKET_HANDLER": {"host": "127.0.0.1", "port": "13254"},
    }
    mock_server = mocker.Mock()
    monkeypatch.setattr(WSHandler, "_setup_server", lambda *x, **y: mock_server)
    close_patcher = mocker.patch.object(mock_server, "shutdown_gracefully")
    ws_handler = WSHandler(config, registrar)
    assert ws_handler._server is None
    ws_handler.connect()
    assert ws_handler._server is not None
    ws_handler.close()
    close_patcher.assert_called_once()
