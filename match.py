from events import InningsStartedEvent, BallCompletedEvent, BatterInningsCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar
from score import Scoreable


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
        ise = InningsStartedEvent.build(payload, registrar, self)
        new_innings = Innings(ise)
        self.match_inningses.append(new_innings)
        return ise

    def on_ball_completed(self, payload: dict, registrar: FixedDataRegistrar):
        innings = self.get_current_innings()
        bce = BallCompletedEvent.build(
            payload,
            innings.get_striker(),
            innings.get_non_striker(),
            innings.get_current_bowler(),
            payload,
        )
        super().on_ball_completed(bce)
        self.get_current_innings().on_ball_completed(bce)
        return bce

    def on_batter_innings_completed(self, payload: dict, registrar: FixedDataRegistrar):
        innings = self.get_current_innings()
        bic = BatterInningsCompletedEvent.build(payload,
                                                registrar)
        innings.on_batter_innings_completed(bic)
        return bic
