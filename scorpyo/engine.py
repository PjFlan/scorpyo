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


# This class should be responsible for receiving a stream of match events (commands)
# processing the event based on its internal state, and spitting out an event message
# that other applications (client, score reporter) can listen to and do their own job
class MatchEngine(Context):

    match_id = 0

    def __init__(self):
        super().__init__()
        self.current_match = None
        self.events = []

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_event(self, event_message: dict):
        event_type = EventType(event_message["event_type"])
        payload = event_message["payload"]
        new_event = self.handle_event(event_type, payload)
        self.events.append(new_event)

    def handle_match_started(self, payload: dict):
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
        home_team.add_line_up(
            self.entity_registrar.get_from_names(
                EntityType.PLAYER, payload["home_line_up"]
            )
        )
        away_team.add_line_up(
            self.entity_registrar.get_from_names(
                EntityType.PLAYER, payload["away_line_up"]
            )
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
        if self.current_match and self.current_match.state == MatchState.IN_PROGRESS:
            raise ValueError(
                f"match_id {self.current_match.match_id} is still in "
                f"progress, cannot start a new match until this is "
                f"completed"
            )
        self.current_match = Match(mse, self)
        self._child_context = self.current_match

    def on_match_completed(self, mce: MatchCompletedEvent):
        self.current_match.state = mce.reason
        # TODO pflanagan: send out a message
