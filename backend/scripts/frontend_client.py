import json
import logging
import os
import time

import websocket

from scorpyo.util import load_config
from test.common import TEST_CONFIG_PATH

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


OUTFILE = "/Users/padraicflanagan/projects/scoring-app/backend/data/sample_msgs.json"

if __name__ == "__main__":
    ws = websocket.WebSocket()

    config = load_config(TEST_CONFIG_PATH)
    host = config["WEB_SOCKET_HANDLER"]["host"]
    port = config["WEB_SOCKET_HANDLER"]["port"]
    home_dir = config["CLIENT"]["root_dir"]
    input_commands = config["WEB_SOCKET_HANDLER"]["test_commands"]
    commands_file = os.path.join(home_dir, input_commands)
    with open(commands_file) as fh:
        time.sleep(0)
        commands = json.loads(fh.read())

    ws.connect(f"ws://{host}:{port}")
    messages = {}
    msg_idx = 0
    for command in commands:
        time.sleep(0)
        ws.send(json.dumps(command))
        resp = ws.recv()
        messages[msg_idx] = json.loads(resp)
        msg_idx += 1
        resp = ws.recv()
        messages[msg_idx] = json.loads(resp)
        msg_idx += 1
        # print(json.dumps(json.loads(resp), indent=4))
    print(messages)
    ws.close()
    with open(OUTFILE, "w") as fh:
        json.dump(messages, fh, indent=4)
