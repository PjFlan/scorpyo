from scorpyo.client import MatchClient, FileSource, json_reader
from scorpyo.engine import MatchEngine


def main():
    client = MatchClient()
    engine = MatchEngine()
    client.assign_engine(engine)
    file_source = FileSource("tests/resources/test_match_input.json", json_reader)
    client.register_sources([file_source])
    with client.connect() as client_:
        client_.read()
        client_.process()


if __name__ == "__main__":
    main()
