import json
import logging
import os

from scorpyo.client.client import EngineClient
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_tcp.ini")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    config = load_config(CONFIG_FILE)
    root_dir = config["MAIN"]["root_dir"]
    registrar = EntityRegistrar(config)
    client = EngineClient(registrar)
    commands = os.path.join(root_dir, config["CLIENT"]["commands"])
    with open(commands) as fh:
        commands = json.load(fh)
        for command in commands:
            resp = client.on_event_command(command)
            print(resp)
