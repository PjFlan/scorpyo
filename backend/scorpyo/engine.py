import enum

from scorpyo.context import Context
from scorpyo.entity import EntityType, Entity
from scorpyo.match import Match, MatchState
from scorpyo.event import (
    EventType,
    MatchStartedEvent,
    MatchCompletedEvent,
)
import scorpyo.util as util
from scorpyo.registrar import EventRegistrar
from scorpyo.definitions.match import get_match_type


# TODO: implement rollback, and pushing processed events onto a listener stream
# If anything goes wrong the engine should lock itself until the issue resolve (but
# not crash). Also need to implement an API for querying the state of the match
# for future applications like MatchReporter to consume and format


class MatchEngine(Context):
    """
    Receives a stream of match events (commands) and processes the event
    based on its internal state, then sends out a corresponding message
    that other applications (client, score reporter) can listen for
    """

    event_registrar = None
    match_id = 0
    message_id = 0

    def __init__(self, entity_registrar: "EntityRegistar"):
        super().__init__()
        self.current_match = None
        self.state: EngineState = EngineState.LOCKED
        self._events = []
        self._score_listeners = []
        self.entity_registrar = entity_registrar
        self.event_registrar = EventRegistrar()

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_event(self, event_command: dict):
        event_type = event_command.get("event")
        if not event_type:
            raise ValueError(
                f"no event_type specified on incoming command " f"{event_command}"
            )
        self._events.append(event_command)
        event_message = self.handle_event(event_type, event_command["body"])
        message = {
            "event": event_type.value,
            "message_id": self.message_id,
            "body": event_message,
        }
        self.message_id += 1
        self.send_message(message)

    def description(self) -> dict:
        return {"engine_user": "pflanagan"}

    def snapshot(self) -> dict:
        # TODO pflanagan: not sure yet what this should return, only there to conform
        #  with Context interface
        return {}

    def overview(self) -> dict:
        return {"description": self.description(), "overview": self.overview()}

    def send_message(self, message: dict):
        for listener in self._score_listeners:
            listener.on_message(message)

    def handle_match_started(self, payload: dict):
        if self.current_match and self.current_match.state == MatchState.IN_PROGRESS:
            raise ValueError(
                f"match_id {self.current_match.match_id} is still in "
                f"progress, cannot start a new match until this is "
                f"completed"
            )
        start_time = util.get_current_time()
        match_type = get_match_type(payload["match_type"])
        # TODO pflanagan: this will be retrieved from persistent storage
        match_id = MatchEngine.match_id
        MatchEngine.match_id += 1
        home_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, payload["home_team"]
        )
        away_team = self.entity_registrar.get_entity_data(
            EntityType.TEAM, payload["away_team"]
        )
        mse = MatchStartedEvent(match_id, match_type, start_time, home_team, away_team)
        message = self.on_match_started(mse)
        return message

    def handle_match_completed(self, payload: dict):
        end_time = util.get_current_time()
        match_id = payload.get("match_id")
        reason = payload.get("reason")
        assert match_id == self.current_match.match_id, (
            "match_id from event payload {match_id} "
            "does not equal current match_id {self.current_match.match_id}"
        )
        mce = MatchCompletedEvent(match_id, end_time, reason)
        self.on_match_completed(mce)
        return mce

    def on_match_started(self, mse: MatchStartedEvent):
        self.current_match = Match(
            mse, self, self.entity_registrar, self.event_registrar
        )
        self._child_context = self.current_match
        return self.current_match.overview()

    def on_match_completed(self, mce: MatchCompletedEvent):
        self.current_match.state = mce.reason
        return self.current_match.overview()

    def register_client(self, client: "EngineClient"):
        self._score_listeners.append(client)


class EngineState(enum.Enum):
    LOCKED = 0
    RUNNING = 1
