from collections import deque
from contextlib import contextmanager
from typing import Optional

from scorpyo.client.handler import ClientHandler, FileHandler, CommandLineHandler
from scorpyo.engine import MatchEngine
from scorpyo.event import EventType
from scorpyo.registrar import EntityRegistrar
from scorpyo.util import load_config


DEFAULT_CFG_DIR = "~/.config/scorpyo/scorpyo.cfg"


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

    def process(self):
        """do something with the new data"""
        while self._handler.is_open:
            self._handler.read()
            for command in self._handler.query():
                self.handle_command(command)

    def handle_command(self, command: dict):
        """interpret a command and send it to the engine, registrar or otherwise"""
        if "body" not in command:
            raise ValueError(f"missing body on incoming command" f" {command}")
        self.on_event_command(command)

    def register_handler(self):
        """a list of handlers, ordered according to which should be consumed first"""
        handler_name = self.config["CLIENT"]["handler"]
        handler_klass = {"file": FileHandler, "cli": CommandLineHandler}[handler_name]
        self._handler = handler_klass(self.config, self.registrar)

    def on_event_command(self, command: dict):
        """pass to the engine for processing and confirm the engine acked the command
        the client should know the internal protocol accepted by the engine and
        format commands accordingly. For now I will maintain this protocol distinctly
        between engine and client but if it grows, may need to move to a protobuf"""
        e_type = command.get("event")
        if not e_type:
            raise ValueError(f"no event type passed in event command")
        try:
            # TODO: probably should be passing in the event id rather than raw string
            event_type = EventType(e_type)
        except KeyError:
            raise ValueError(f"event command payload has an invalid type {e_type}")
        if "body" not in command:
            raise ValueError(f"no data passed in event command")
        command["command_id"] = self.engine_sequence
        command["event"] = event_type
        self.engine_sequence += 1
        self._pending_commands.append(command)
        self.engine.on_event(command)

    def on_message(self, message: dict):
        message_id = message.get("message_id")
        if message_id is None:
            raise ValueError(f"received message from engine with know id {message}")
        if len(self._pending_commands) == 0:
            raise ValueError(f"received message from engine without pending commands")
        oldest_command = self._pending_commands.popleft()
        command_id = oldest_command["command_id"]
        assert message_id == command_id, (
            f"message_id does not match command_id of "
            "oldest pending command {message_id} != {command_id}"
        )
        self._handler.on_message(message)

    @contextmanager
    def connect(self):
        """connect to registered handler to begin receiving commands"""
        self.engine.register_client(self)
        self._handler.connect()
        yield self
        self._handler.close()
