from scorpyo.client.client import MatchClient
from scorpyo.engine import MatchEngine
from scorpyo.registrar import EntityRegistrar
from tests.common import TEST_CONFIG, TEST_CONFIG_PATH


def main():
    registrar = EntityRegistrar(TEST_CONFIG)
    engine = MatchEngine(registrar)
    client = MatchClient(registrar, engine, TEST_CONFIG_PATH)
    with client.connect() as client_:
        client_.process()


if __name__ == "__main__":
    main()
