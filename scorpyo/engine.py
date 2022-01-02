from scorpyo.context import Context
from scorpyo.fixed_data import Entity
from scorpyo.match import Match, MatchState
from scorpyo.events import (
    EventType,
    MatchStartedEvent,
    MatchCompletedEvent,
)
import scorpyo.util as util
from scorpyo.static_data.match import get_match_type


class MatchEngine(Context):
    def __init__(self):
        super().__init__()
        self.current_match = None

        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)
        self.add_handler(EventType.MATCH_COMPLETED, self.handle_match_completed)

    def on_event(self, event_message: dict):
        event_type = EventType(event_message["event_type"])
        payload = event_message["payload"]
        new_event = self.handle_event(event_type, payload)
        # TODO: implement storing the event stream for replaying
        """
        if new_event:
            self.event_registrar.add(new_event)
        """

    def handle_match_started(self, payload: dict):
        start_time = util.get_current_time()
        match_type = get_match_type(payload["match_type"])
        match_id = int(start_time)
        home_team = self.fd_registrar.get_fixed_data(Entity.TEAM, payload["home_team"])
        away_team = self.fd_registrar.get_fixed_data(Entity.TEAM, payload["away_team"])
        home_team.add_line_up(
            self.fd_registrar.get_from_names(Entity.PLAYER, payload["home_line_up"])
        )
        away_team.add_line_up(
            self.fd_registrar.get_from_names(Entity.PLAYER, payload["away_line_up"])
        )
        mse = MatchStartedEvent(match_id, match_type, start_time, home_team, away_team)
        self.on_match_started(mse)
        return mse

    def handle_match_completed(self, payload: dict):
        end_time = util.get_current_time()
        match_id = payload["match_id"]
        assert match_id != self.match_id, (
            "match_id from event payload {match_id} "
            "does not equal current match_id {self.match_id}"
        )
        mce = MatchCompletedEvent(end_time)
        self.on_match_completed(mce)
        return mce

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
