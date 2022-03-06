import builtins
import json
from io import StringIO
from typing import List

import pytest

from scorpyo.client import MatchClient, FileSource, json_reader
from scorpyo.engine import MatchEngine
from scorpyo.registrar import EntityRegistrar
from tests.common import TEST_CONFIG_PATH

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
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    with my_client.connect() as client:
        assert len(client._sources) == 1
        assert client._sources[0].is_open()
    assert not my_client._sources[0].is_open()


def test_file_source_plain_reader(registrar, mock_file, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {"FILE_SOURCE": {"url": "/path/to/url", "reader": "plain"}}
    file_source = FileSource(config, registrar)
    file_source.connect()
    mock_file.write_lines(LINES[0:2])
    file_source.read()
    assert len(file_source.command_buffer) == 2
    mock_file.write(LINES[2])
    file_source.read()
    assert len(file_source.command_buffer) == 3
    read_lines = []
    for line in file_source.query():
        read_lines.append(line)
    assert read_lines == LINES
    file_source.close()


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
        client.read()
    assert mock_client._sources[0].has_data()
    mock_client.process()
    assert patched.call_count == 3
    assert not mock_client._sources[0].has_data()


def test_client_json_reader(mock_file, mocker, registrar, mock_engine, monkeypatch):
    monkeypatch.setattr(builtins, "open", lambda x, y: mock_file)
    config = {
        "CLIENT": {"source": "file"},
        "FILE_SOURCE": {"url": "/path/to/url", "reader": "json"},
    }
    mock_client = MatchClient(registrar, mock_engine, config)
    mock_client._sources[0].reader = json_reader
    mock_file.write(TEST_JSON)
    patched = mocker.patch.object(MatchClient, "handle_command")
    with mock_client.connect() as client:
        client.read()
    assert mock_client._sources[0].has_data()
    mock_client.process()
    assert patched.call_count == 3
    assert not mock_client._sources[0].has_data()


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
