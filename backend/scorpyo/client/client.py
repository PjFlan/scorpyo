import logging
from collections import deque
from contextlib import contextmanager
from time import sleep
from typing import Optional

from scorpyo.client.handler import (
    ClientHandler,
    FileHandler,
    CommandLineHandler,
    WSHandler,
)
from scorpyo.engine import MatchEngine
from scorpyo.error import RejectReason, ClientError
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config, LOGGER


DEFAULT_CFG_DIR = "~/.config/scorpyo/scorpyo.cfg"
DEFAULT_TIMEOUT = 0.5

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class EngineClient:
    def __init__(
        self, registrar: EntityRegistrar, engine: MatchEngine, config=DEFAULT_CFG_DIR
    ):
        self.registrar = registrar
        self.engine = engine
        self._pending_commands: deque = deque()
        self.engine_sequence = 0
        if isinstance(config, str):
            self.config = load_config(config)
        elif isinstance(config, dict):
            self.config = config
        self._handler: Optional[ClientHandler] = None
        self.register_handler()
        try:
            self._timeout = int(self.config["CLIENT"]["power_save_timeout"])
        except (KeyError, ValueError):
            self._timeout = DEFAULT_TIMEOUT

    def process(self):
        """do something with the new data"""
        while self._handler.is_open:
            self._handler.read()
            for command in self._handler.query():
                self.handle_command(command)
            sleep(self._timeout)

    def handle_command(self, command: dict):
        """interpret a command and send it to the engine after validating"""
        try:
            self.on_event_command(command)
        except ClientError as e:
            self._handler.on_message(e.compile())

    def register_handler(self):
        """a list of handlers, ordered according to which should be consumed first"""
        handler_name = self.config["CLIENT"]["handler"]
        handler_klass = {
            "file": FileHandler,
            "cli": CommandLineHandler,
            "ws": WSHandler,
        }[handler_name]
        self._handler = handler_klass(self.config, self.registrar)

    def on_event_command(self, command: dict):
        """pass to the engine for processing and confirm the engine acked the command
        the client should know the internal protocol accepted by the engine and
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
        if "body" not in command:
            msg = "no data passed in event command"
            LOGGER.warning(msg)
            raise ClientError(msg, RejectReason.BAD_COMMAND)
        command["command_id"] = self.engine_sequence
        command["event"] = event_type
        self._pending_commands.append(command)
        self.engine.on_command(command)
        self.engine_sequence += 1

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

    @contextmanager
    def connect(self):
        """connect to registered handler to begin receiving commands"""
        self.engine.register_client(self)
        self._handler.connect()
        try:
            yield self
        finally:
            logging.info("closing handler")
            self._handler.close()
