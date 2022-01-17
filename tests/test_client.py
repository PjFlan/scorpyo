import builtins
from io import StringIO

from scorpyo.client import MatchClient, FileSource
from scorpyo.engine import MatchEngine


def test_client_setup(mock_engine: MatchEngine, monkeypatch):
    my_client = MatchClient(mock_engine)
    monkeypatch.setattr(builtins, "open", lambda x, y: StringIO())
    file_source = FileSource("path/to/resource")
    my_client.register_sources([file_source])
    with my_client.connect() as client:
        assert len(client._sources) == 1
        assert client._sources[0].is_open()
    assert not my_client._sources[0].is_open()
