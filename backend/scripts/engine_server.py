import os

from scorpyo.client.client import EngineClient
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config


CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config_ws.ini")


def main():
    config = load_config(CONFIG_PATH)
    registrar = EntityRegistrar(config)
    client = EngineClient(registrar, config)
    with client.connect() as client_:
        client_.process()


if __name__ == "__main__":
    main()
