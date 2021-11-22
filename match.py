from events import InningsStartedEvent, BallCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar
from util import Scoreable


class Match(Scoreable):
    def __init__(self, match_started_event):
        super().__init__()
        self.match_id = match_started_event.match_id
        self.start_time = match_started_event.start_time
        self.match_type = match_started_event.match_type
        self.home_team = match_started_event.home_team
        self.away_team = match_started_event.away_team
        self.match_inningses = []

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

    def on_new_innings(self, payload: dict, registrar: FixedDataRegistrar):
        if len(self.match_inningses) == self.get_max_innings():
            raise ValueError(f"Match already has {self.get_max_innings()} innings")
        if len(self.match_inningses) > 0 and not self.match_inningses[-1].is_complete:
            raise ValueError("Previous innings has not yet ended.")
        innings_started_event = InningsStartedEvent.build(payload, registrar, self)
        new_innings = Innings(innings_started_event)
        self.match_inningses.append(new_innings)
        return innings_started_event

    def on_ball_completed(self, payload: dict, registrar: FixedDataRegistrar):
        ball_completed_event = BallCompletedEvent.build(payload, registrar)
        super().on_ball_completed(ball_completed_event)
        self.get_current_innings().on_ball_completed(ball_completed_event)
        return ball_completed_event
