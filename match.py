import util
from context import Context
from events import (
    BallCompletedEvent,
    BatterInningsCompletedEvent,
    InningsStartedEvent,
    BatterInningsStartedEvent,
    MatchStartedEvent,
    EventType,
)
from fixed_data import Entities, Entities
from innings import Innings
from score import Scoreable


# TODO: I don't like multiple inheritance here
# eventually I will probably need to create a new MatchContext
# class, separate from Match
class Match(Context, Scoreable):
    def __init__(self, mse: MatchStartedEvent, match_engine: "MatchEngine"):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match_engine = match_engine
        self.match_id = mse.match_id
        self.start_time = mse.start_time
        self.match_type = mse.match_type
        self.home_team = mse.home_team
        self.away_team = mse.away_team
        self.match_inningses = []
        self.add_handler(EventType.INNINGS_STARTED, self.handle_innings_started)

    def get_max_overs(self):
        return self.match_type.overs

    def get_max_innings(self):
        return self.match_type.innings

    def get_num_innings(self):
        return len(self.match_inningses)

    def get_teams(self):
        return [self.home_team, self.away_team]

    def get_current_innings(self):
        return self.match_inningses[-1]

    def add_innings(self, innings: Innings):
        self.match_inningses.append(innings)

    def validate(self):
        if len(self.match_inningses) == self.get_max_innings():
            raise ValueError(f"Match already has {self.get_max_innings()} innings")
        if len(self.match_inningses) > 0 and not self.match_inningses[-1].is_complete:
            raise ValueError("Previous innings has not yet ended.")

    def handle_innings_started(self, payload: dict):
        start_time = util.get_current_time()
        innings_id = self.get_num_innings()  # index innings from 0 not 1
        batting_team = self.fd_registrar.get_fixed_data(
            Entities.TEAM, payload["batting_team"]
        )
        bowling_team = [team for team in self.get_teams() if team != batting_team][0]
        opening_bowler = self.fd_registrar.get_fixed_data(
            Entities.PLAYER, payload["opening_bowler"]
        )
        ise = InningsStartedEvent(
            innings_id, start_time, batting_team, bowling_team, opening_bowler
        )
        self.on_innings_started(ise)
        return ise

    def on_innings_started(self, ise: InningsStartedEvent):
        new_innings = Innings(ise, self)
        self.add_innings(new_innings)
        self._child_context = new_innings

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
        self.get_current_innings().on_ball_completed(bce)

    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent):
        self.get_current_innings().on_batter_innings_completed(bic)

    def on_batter_innings_started(self, bis: BatterInningsStartedEvent):
        self.get_current_innings().on_batter_innings_started(bis)
