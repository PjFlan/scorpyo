import json
import logging
import os

import websocket

from scorpyo.util import load_config
from test.common import TEST_CONFIG_PATH

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


if __name__ == "__main__":
    ws = websocket.WebSocket()

    config = load_config(TEST_CONFIG_PATH)
    host = config["WEB_SOCKET_HANDLER"]["host"]
    port = config["WEB_SOCKET_HANDLER"]["port"]
    home_dir = config["CLIENT"]["root_dir"]
    input_commands = config["WEB_SOCKET_HANDLER"]["test_commands"]
    commands_file = os.path.join(home_dir, input_commands)
    with open(commands_file) as fh:
        commands = json.loads(fh.read())

    ws.connect(f"ws://{host}:{port}")
    for command in commands:
        ws.send(json.dumps(command))
        reply = ws.recv()
        logger.info("received message from engine: " + reply)
    ws.close()
