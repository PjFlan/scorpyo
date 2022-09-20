from scorpyo.client.client import EngineClient
from scorpyo.registrar import EntityRegistrar
from test.common import TEST_CONFIG_PATH


def main():
    registrar = EntityRegistrar(TEST_CONFIG_PATH)
    client = EngineClient(registrar, TEST_CONFIG_PATH)
    with client.connect() as client_:
        client_.process()


if __name__ == "__main__":
    main()
