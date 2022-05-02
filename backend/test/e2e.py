from scorpyo.client.client import EngineClient
from scorpyo.engine import MatchEngine
from scorpyo.registrar import EntityRegistrar
from test.common import TEST_ENTITIES_CONFIG, TEST_CONFIG_PATH


def main():
    registrar = EntityRegistrar(TEST_ENTITIES_CONFIG)
    engine = MatchEngine(registrar)
    client = EngineClient(registrar, engine, TEST_CONFIG_PATH)
    with client.connect() as client_:
        client_.process()


if __name__ == "__main__":
    main()
