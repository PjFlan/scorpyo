import json
import logging
import time

from scorpyo.client.handler import WSHandler

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


INFILE = "/Users/padraicflanagan/projects/scoring-app/backend/data/sample_msgs.json"


def main():
    config = {"WEB_SOCKET_HANDLER": {"host": "127.0.0.1", "port": 13254}}
    ws_handler = WSHandler(config, None)
    ws_handler.connect()
    with open(INFILE) as fh:
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
