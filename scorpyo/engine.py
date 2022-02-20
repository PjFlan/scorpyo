import enum

from scorpyo.context import Context
from scorpyo.entity import EntityType
from scorpyo.match import Match, MatchState
from scorpyo.events import (
    EventType,
    MatchStartedEvent,
    MatchCompletedEvent,
)
import scorpyo.util as util
from scorpyo.static_data.match import get_match_type


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

    match_id = 0

    def __init__(self):
        super().__init__()
        self.current_match = None
        self.state: EngineState = EngineState.LOCKED
        self._events = []
        self._score_listeners = []

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_event(self, event_type: EventType, event_payload: dict):
        # TODO pflanagan: need to upgrade all the handlers to send a message back as
        #  part of their processing
        self._events.append(event_payload)
        event_message = self.handle_event(event_type, event_payload)
        return event_message

    def produce_snapshot(self) -> dict:
        # TODO pflanagan: not sure yet what this should return, only there to conform
        #  with Context interface
        return {}

    def status(self):
        if not self.current_match:
            return
        output = self.current_match.status()
        for listener in self._score_listeners:
            listener.on_match_update(output)

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
        self.on_match_started(mse)
        return mse

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
        self.current_match = Match(mse, self)
        self._child_context = self.current_match

    def on_match_completed(self, mce: MatchCompletedEvent):
        self.current_match.state = mce.reason
        # TODO pflanagan: send out a message

    def on_client_registered(self, client: "MatchClient"):
        self._score_listeners.append(client)


class EngineState(enum.Enum):
    LOCKED = 0
    RUNNING = 1
