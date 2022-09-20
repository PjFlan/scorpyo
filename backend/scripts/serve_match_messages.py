import json
import logging
import os
import time

from scorpyo.client.handler import WSHandler
from scorpyo.util import load_config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


CONFIG = os.path.join(os.path.dirname(__file__), "config_ws.ini")


def main():
    config = load_config(CONFIG)
    ws_config = config["WEB_SOCKET_HANDLER"]
    infile = config["CLIENT"]["root_dir"]
    ws_handler = WSHandler(ws_config)
    ws_handler.connect()
    with open(infile) as fh:
        messages = json.load(fh).values()
    while ws_handler.num_clients == 0:
        time.sleep(0.5)
        continue
    print("found a client")
    for message in messages:
        ws_handler.on_message(message)
        time.sleep(0.5)
    ws_handler.close()


if __name__ == "__main__":
    main()
