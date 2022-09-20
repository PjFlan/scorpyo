import json
import logging
import os
import time

import websocket

from scorpyo.util import load_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_ws.ini")


if __name__ == "__main__":
    ws = websocket.WebSocket()

    config = load_config(CONFIG_FILE)
    host = config["WEB_SOCKET_HANDLER"]["host"]
    port = config["WEB_SOCKET_HANDLER"]["port"]
    home_dir = config["MAIN"]["root_dir"]
    outfile = os.path.join(home_dir, "data", "sample_msgs.json")
    input_commands = config["WEB_SOCKET_HANDLER"]["commands"]
    commands_file = os.path.join(home_dir, input_commands)
    with open(commands_file) as fh:
        time.sleep(0)
        commands = json.loads(fh.read())

    ws.connect(f"ws://{host}:{port}")
    messages = []
    for command in commands:
        time.sleep(0)
        ws.send(json.dumps(command))
        resp = ws.recv()
        messages.append(json.loads(resp))
        resp = ws.recv()
        messages.append(json.loads(resp))
        # print(json.dumps(json.loads(resp), indent=4))
    print(messages)
    ws.close()
    with open(outfile, "w") as fh:
        json.dump(messages, fh, indent=4)
