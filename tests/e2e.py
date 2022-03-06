import os.path

from scorpyo.client import MatchClient, FileSource, json_reader
from scorpyo.engine import MatchEngine
from scorpyo.registrar import EntityRegistrar
from tests.common import RESOURCES_PATH, TEST_CONFIG, TEST_CONFIG_PATH


def main():
    registrar = EntityRegistrar(TEST_CONFIG)
    engine = MatchEngine(registrar)
    client = MatchClient(registrar, engine, TEST_CONFIG_PATH)
    test_event_source = os.path.join(RESOURCES_PATH, "test_match_input.json")
    file_source = FileSource(test_event_source, json_reader)
    client.register_sources([file_source])
    with client.connect() as client_:
        client_.read()
        client_.process()


if __name__ == "__main__":
    main()
