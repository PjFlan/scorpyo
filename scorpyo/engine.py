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


class MatchEngine(Context):
    """
    Receives a stream of match events (commands) and processes the event
    based on its internal state, then sends out a corresponding event message
    that other applications (client, score reporter) can listen for
    """

    match_id = 0

    def __init__(self):
        super().__init__()
        self.current_match = None
        self.state = EngineState.LOCKED
        self._events = []
        self._clients = []

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_event(self, event_message: dict):
        event_type = EventType(event_message["event_type"])
        payload = event_message["payload"]
        new_event = self.handle_event(event_type, payload)
        self._events.append(new_event)

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
        match_id = payload["match_id"]
        reason = MatchState(payload["reason"])
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
        self._clients.append(client)


class EngineState(enum.Enum):
    LOCKED = 0
    RUNNING = 1
