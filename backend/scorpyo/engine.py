import enum
import json
import socket

from scorpyo.context import Context
from scorpyo.entity import EntityType
from scorpyo.error import EngineError, RejectReason
from scorpyo.match import Match, MatchState
from scorpyo.event import (
    EventType,
    MatchStartedEvent,
    MatchCompletedEvent,
)
import scorpyo.util as util
from scorpyo.util import LOGGER
from scorpyo.registrar import CommandRegistrar, EntityRegistrar
from scorpyo.definitions.match import get_match_type

"""
TODO pflanagan: implement rollback

TODO pflanagan: should each context object have some sort of validator dependency
that can wrap all of the validation for a given command? Otherwise I have validation
scattered around - need to consolidate.
"""


class MatchEngine(Context):
    """
    Receives a stream of match events (commands) and processes the event
    based on its internal state, then sends out a corresponding message
    that other applications (client, score reporter) can listen for
    """

    def __init__(self, entity_registrar: "EntityRegistar"):
        super().__init__()
        self.match_id = 0
        self.message_id = 0
        self.current_match = None
        self.state: EngineState = EngineState.LOCKED
        self._events = []
        self._messages = []
        self._score_listeners = []
        self.entity_registrar = entity_registrar
        self.command_registrar = CommandRegistrar()

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_command(self, command: dict):
        try:
            message = self.process_command(command)
        except EngineError as e:
            message = e.compile()
        message["message_id"] = self.message_id
        self.message_id += 1
        self._messages.append(message)
        self.send_message(message, is_snapshot=False)
        if self.current_match:
            snapshot_msg = self.current_match.snapshot()
            self.send_message(snapshot_msg, is_snapshot=True)
        return message

    def process_command(self, command: dict):
        try:
            event_type_code = command["event"]
            command_id = command["command_id"]
        except KeyError:
            msg = f"no event_type or command_id specified on incoming command {command}"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        next_sequence = self.message_id
        if command_id != next_sequence:
            msg = (
                f"command_id from client out of sequence with engine client="
                f"{command_id}, engine={next_sequence}"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        self._events.append(command)
        try:
            event_type = EventType(event_type_code)
        except ValueError:
            msg = f"invalid event type {event_type_code}"
            LOGGER.error(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        resp = self.handle_event(event_type, command["body"])
        message = self.create_message(event_type, resp)
        return message

    def description(self) -> dict:
        return {"engine_user": "pflanagan"}

    def snapshot(self) -> dict:
        # TODO pflanagan: not sure yet what this should return, only there to conform
        #  with Context interface for now
        return {}

    def overview(self) -> dict:
        return {"description": self.description(), "overview": self.snapshot()}

    def send_message(self, message: dict, is_snapshot=False):
        message["is_snapshot"] = is_snapshot
        for listener in self._score_listeners:
            listener.on_message(message)

    def handle_match_started(self, payload: dict):
        try:
            match_type_shortname = payload["match_type"]
        except KeyError:
            msg = "must specify match_type on new match command"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        if self.current_match and self.current_match.state == MatchState.IN_PROGRESS:
            msg = (
                f"match_id {self.current_match.match_id} is still in "
                f"progress, cannot start a new match until this is completed"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        start_time = util.get_current_time()
        try:
            match_type = get_match_type(match_type_shortname)
        except ValueError:
            msg = f"invalid match type: {match_type_shortname}"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        home_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, payload["home_team"]
        )
        away_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, payload["away_team"]
        )
        mse = MatchStartedEvent(
            self.match_id, match_type, start_time, home_team, away_team
        )
        message = self.on_match_started(mse)
        return message

    def handle_match_completed(self, payload: dict):
        end_time = util.get_current_time()
        match_id = payload.get("match_id")
        reason = payload.get("reason")
        if match_id != self.current_match.match_id:
            msg = (
                "match_id from event payload {match_id} does not equal "
                "current match_id {self.current_match.match_id}"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        mce = MatchCompletedEvent(match_id, end_time, reason)
        self.on_match_completed(mce)
        return mce

    def on_match_started(self, mse: MatchStartedEvent):
        self.current_match = Match(
            mse, self, self.entity_registrar, self.command_registrar
        )
        self._child_context = self.current_match
        return self.current_match.overview()

    def on_match_completed(self, mce: MatchCompletedEvent):
        self.current_match.state = mce.reason
        return self.current_match.overview()

    def register_client(self, client: "EngineClient"):
        self._score_listeners.append(client)

    def create_message(self, event_type: EventType, message: dict):
        message = {
            "event": event_type.value,
            "body": message,
        }
        return message


def run_server():
    config = util.load_config()
    registrar = EntityRegistrar(config)
    engine = MatchEngine(registrar)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((config["ENGINE"]["host"], config.getint("ENGINE", "port")))
        s.listen()
        while True:
            conn, address = s.accept()
            with conn:
                print(f"Connected by {address}")
                full_message = ""
                while True:
                    data = conn.recv(1024)
                    if not data:
                        break
                    full_message += data.decode()
                    json_command = json.loads(full_message)
                    resp = engine.on_command(json_command)
                    resp_str = json.dumps(resp)
                    conn.sendall(resp_str.encode())


class EngineState(enum.Enum):
    LOCKED = 0
    RUNNING = 1


if __name__ == "__main__":
    run_server()
