import json
import logging
import socket
from collections import deque
from contextlib import contextmanager
from time import sleep
from typing import Optional

from websocket_server import WebsocketServer

from scorpyo.client.handler import (
    FileHandler,
    CommandLineHandler,
    WSHandler,
    ClientHandler,
)
from scorpyo.error import RejectReason, ClientError
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config, LOGGER


DEFAULT_TIMEOUT = 0.5


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EngineClient:
    def __init__(self, registrar: EntityRegistrar, config_path: Optional[str] = None):
        self.registrar = registrar
        self._pending_commands: deque = deque()
        self.engine_sequence = 0
        self.config = load_config(config_path)
        self._handler: ClientHandler = self.create_handler()
        self._timeout = self.config.getfloat(
            "CLIENT", "power_save_timeout", fallback=DEFAULT_TIMEOUT
        )
        self.engine_host = self.config["ENGINE"]["host"]
        self.engine_port = self.config.getint("ENGINE", "port")
        open_websocket = self.config.getboolean("CLIENT", "create_ws", fallback=False)
        if open_websocket:
            port = self.config.getint("CLIENT", "ws_port")
            host = self.config["CLIENT"]["ws_host"]
            self._websocket = create_websocket(host, port)

    def process(self):
        """do something with the new data"""
        while self._handler.is_open:
            self._handler.read()
            for command in self._handler.query():
                sleep(self._timeout)
                self.handle_command(command)

    def handle_command(self, command: dict):
        """interpret a command and send it to the engine after validating"""
        try:
            self.on_event_command(command)
        except ClientError as e:
            self._handler.on_message(e.compile())

    def create_handler(self):
        """a list of handlers, ordered according to which should be consumed first"""
        handler_name = self.config.get("CLIENT", "handler", fallback=None)
        if not handler_name:
            return
        handler_klass = {
            "file": FileHandler,
            "cli": CommandLineHandler,
            "ws": WSHandler,
        }[handler_name]
        return handler_klass(self.config)

    def on_event_command(self, command: dict):
        """pass to the engine for processing and confirm the engine acked the command.
        The client should know the internal protocol accepted by the engine and
        format commands accordingly. For now I will maintain this protocol distinctly
        between engine and client but if it grows, may need to move to a protobuf"""
        if "body" not in command:
            msg = f"missing body on incoming command" f" {command}"
            LOGGER.warning(msg)
            raise ClientError(msg, RejectReason.BAD_COMMAND)
        e_type = command.get("event")
        if not e_type:
            msg = "no event type passed in event command"
            LOGGER.warning(msg)
            raise ClientError(msg, RejectReason.BAD_COMMAND)
        try:
            event_type = EventType(e_type)
        except KeyError:
            msg = f"event command payload has an invalid type {e_type}"
            LOGGER.warning(msg)
            raise ClientError(msg, RejectReason.BAD_COMMAND)
        command["command_id"] = self.engine_sequence
        self._pending_commands.append(command)
        resp = self._send_command(command)
        self.engine_sequence += 1
        return resp

    def _send_command(self, command: dict):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            command_str = json.dumps(command)
            s.connect((self.engine_host, self.engine_port))
            encoded = command_str.encode()
            s.sendall(encoded)
            resp = s.recv(1024)
            resp_str = resp.decode()
            resp_json = json.loads(resp_str)
        return resp_json

    def _validate_message(self, message: dict):
        if not message["is_snapshot"]:
            message_id = message.get("message_id")
            if message_id is None:
                msg = f"received message from engine with no id {message}"
                LOGGER.error(msg)
                raise ClientError(
                    f"received message from engine with no id " f"{message}",
                    RejectReason.INCONSISTENT_STATE,
                )
            if len(self._pending_commands) == 0:
                msg = f"received message from engine without pending commands"
                LOGGER.error(msg)
                raise ClientError(msg, RejectReason.INCONSISTENT_STATE)
            oldest_command = self._pending_commands.popleft()
            command_id = oldest_command["command_id"]
            if message_id != command_id:
                msg = (
                    f"message_id does not match command_id of oldest pending "
                    f"command {message_id} != {command_id}"
                )
                LOGGER.error(msg)
                raise ClientError(msg, RejectReason.INCONSISTENT_STATE)

    def on_message(self, message: dict):
        self._validate_message(message)
        self._handler.on_message(message)
        if self._websocket:
            self._websocket.send_message_to_all(json.dumps(message))

    @contextmanager
    def connect(self):
        """connect to registered handler to begin receiving commands"""
        self._handler.connect()
        try:
            yield self
        finally:
            logging.info("closing handler")
            self._handler.close()


def create_websocket(host: str, port: int):
    server = WebsocketServer(host=host, port=port)
    server.run_forever(threaded=True)
    return server
