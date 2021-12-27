from context import Context
from fixed_data import Nameable
from match import Match
from events import (
    EventType,
    MatchStartedEvent,
)
import util
from static_data.match import get_match_type


class MatchEngine(Context):
    def __init__(self):
        super().__init__()
        self.current_match = None
        self.add_handler(EventType.MATCH_STARTED, self.handle_match_started)

    def on_event(self, event_message: dict):
        event_type = EventType(event_message["event_type"])
        payload = event_message["payload"]
        new_event = self.handle_event(event_type, payload)
        """
        if event_type == EventType.MATCH_STARTED.value:
            new_event = MatchStartedEvent.build(payload, self.fd_registrar)
            self.current_match = Match(new_event)
        elif event_type == EventType.INNINGS_STARTED.value:
            self.current_match.validate()
            new_event = InningsStartedEvent.build(payload, self.fd_registrar, self)
            self.current_match.on_new_innings(new_event)
        elif event_type == EventType.BALL_COMPLETED.value:
            curr_innings = self.current_match.get_current_innings()
            new_event = BallCompletedEvent.build(
                payload,
                curr_innings.get_striker(),
                curr_innings.get_non_striker(),
                curr_innings.get_current_bowler(),
                self.fd_registrar,
            )
            self.current_match.on_ball_completed(new_event)
        elif new_event == EventType.BATTER_INNINGS_COMPLETE.value:
            new_event = BatterInningsCompletedEvent.build(payload, self.fd_registrar)
            self.current_match.on_batter_innings_completed(new_event)
        elif new_event == EventType.BATTER_INNINGS_STARTED.value:
            new_event = BatterInningsStartedEvent.build(
                payload, self.fd_registrar, self.current_match.get_current_innings()
            )
            self.current_match.on_batter_innings_started(new_event)
        else:
            raise ValueError(f"Unrecognised event: {event_type}")
        """
        # TODO: implement storing the event stream
        """
        if new_event:
            self.event_registrar.add(new_event)
        """

    def handle_match_started(self, payload: dict):
        start_time = util.get_current_time()
        match_type = get_match_type(payload["match_type"])
        match_id = int(start_time)
        home_team = self.fd_registrar.get_fixed_data(
            Nameable.TEAM, payload["home_team"]
        )
        away_team = self.fd_registrar.get_fixed_data(
            Nameable.TEAM, payload["away_team"]
        )
        home_team.add_line_up(
            self.fd_registrar.get_from_names(Nameable.PLAYER, payload["home_line_up"])
        )
        away_team.add_line_up(
            self.fd_registrar.get_from_names(Nameable.PLAYER, payload["away_line_up"])
        )
        mse = MatchStartedEvent(match_id, match_type, start_time, home_team, away_team)
        self.on_match_started(mse)
        return mse

    def on_match_started(self, mse: MatchStartedEvent):
        self.current_match = Match(mse)
        self._child_context = self.current_match
