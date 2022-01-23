import builtins
import json
from io import StringIO
from typing import List

import pytest

from scorpyo.client import MatchClient, FileSource, json_reader, plain_reader
from scorpyo.engine import MatchEngine
from scorpyo.entity import EntityType

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
def mock_client(mock_engine: MatchEngine):
    my_client = MatchClient(mock_engine)
    file_source = FileSource("path/to/resource", plain_reader)
    my_client.register_sources([file_source])
    return my_client


def test_client_setup(mock_engine: MatchEngine, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    my_client = MatchClient(mock_engine)
    file_source = FileSource("", plain_reader)
    my_client.register_sources([file_source])
    with my_client.connect() as client:
        assert len(client._sources) == 1
        assert client._sources[0].is_open()
    assert not my_client._sources[0].is_open()


def test_file_source_plain_reader(monkeypatch, mock_file):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    file_source = FileSource("", plain_reader)
    file_source.connect()
    mock_file.write_lines(LINES[0:2])
    file_source.read()
    assert len(file_source.message_buffer) == 2
    mock_file.write(LINES[2])
    file_source.read()
    assert len(file_source.message_buffer) == 3
    read_lines = []
    for line in file_source.query():
        read_lines.append(line)
    assert read_lines == LINES
    file_source.close()


def test_file_source_json_reader(monkeypatch, mock_file):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    file_source = FileSource("", json_reader)
    file_source.connect()
    mock_file.write(TEST_JSON)
    file_source.read()
    assert len(file_source.message_buffer) == 3
    read_lines = []
    for line in file_source.query():
        read_lines.append(line)
    assert read_lines == json.loads(TEST_JSON)
    file_source.close()


def test_client_plain_reader(mock_client, mock_file, mocker, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    mock_file.write_lines(LINES)
    patched = mocker.patch.object(MatchClient, "handle_message")
    with mock_client.connect() as client:
        client.read()
    assert mock_client._sources[0].has_data()
    mock_client.process()
    assert patched.call_count == 3
    assert not mock_client._sources[0].has_data()


def test_client_json_reader(mock_client, mock_file, mocker, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    mock_client._sources[0].reader = json_reader
    mock_file.write(TEST_JSON)
    patched = mocker.patch.object(MatchClient, "handle_message")
    with mock_client.connect() as client:
        client.read()
    assert mock_client._sources[0].has_data()
    mock_client.process()
    assert patched.call_count == 3
    assert not mock_client._sources[0].has_data()


def test_message_handler(mock_client, mocker):
    test_message_1 = {"message_type": "entity", "body": {"dummy1": "test"}}
    entity_patch = mocker.patch.object(MatchClient, "on_entity_message")
    event_patch = mocker.patch.object(MatchClient, "on_event_message")
    mock_client.handle_message(test_message_1)
    assert entity_patch.called_with(test_message_1["body"])
    test_message_2 = {"message_type": "event", "body": {"dummy2": "test"}}
    mock_client.handle_message(test_message_2)
    assert event_patch.called_with(test_message_2["body"])


def test_message_handler_errors(mock_client):
    with pytest.raises(ValueError):
        bad_message = {"message_type": "not exist", "body": "nothing"}
        mock_client.handle_message(bad_message)
    with pytest.raises(ValueError):
        bad_message = {"message_type": "entity"}
        mock_client.handle_message(bad_message)
    with pytest.raises(ValueError):
        bad_message = {"body": "data"}
        mock_client.handle_message(bad_message)


def test_entity_player_message(mock_client):
    test_player = "Padraic Flanagan"
    entity_player_message = {
        "message_type": "entity",
        "body": {"entity_type": "player", "name": test_player},
    }
    mock_client.handle_message(entity_player_message)
    reg_entry = mock_client.registrar.get_entity_data(EntityType.PLAYER, test_player)
    assert reg_entry.name == test_player


def test_entity_team_message(mock_client):
    test_team = "YMCA CC"
    entity_team_message = {
        "message_type": "entity",
        "body": {"entity_type": "team", "name": test_team},
    }
    mock_client.handle_message(entity_team_message)
    reg_entry = mock_client.registrar.get_entity_data(EntityType.TEAM, test_team)
    assert reg_entry.name == test_team


def test_entity_message_errors(mock_client):
    with pytest.raises(ValueError) as exc:
        mock_client.on_entity_message({"test": "nothing"})
    assert exc.match("entity message is missing entity type")
    with pytest.raises(ValueError) as exc:
        mock_client.on_entity_message({"entity_type": "nothing"})
    assert exc.match("entity message payload has an invalid type")
    with pytest.raises(ValueError) as exc:
        mock_client.on_entity_message({"entity_type": "player"})
    assert exc.match("entity message must have at least an entity name")


def test_event_message(mock_client):
    pass
