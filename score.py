import abc
import re


class Score:

    SCORE_PATTERN = re.compile("(?P<num>[0-9]+)?(?P<mod>[a-zA-Z]+)?")

    def __init__(
        self,
        runs_off_bat,
        wide_runs,
        leg_byes,
        byes,
        no_ball_runs,
        penalty_runs,
        wickets,
    ):
        self.runs_off_bat = runs_off_bat
        self.wide_runs = wide_runs
        self.leg_byes = leg_byes
        self.byes = byes
        self.no_ball_runs = no_ball_runs
        self.penalty_runs = penalty_runs
        self.wickets = wickets
        self.valid_deliveries = 0
        self.wide_deliveries = 0

    @classmethod
    def from_tuple(cls, *args):
        new_score = cls(*args)
        new_score.set_calculated_data()
        return new_score

    def set_calculated_data(self):
        self.valid_deliveries = int(self.is_valid_delivery())
        self.wide_deliveries = 1 if self.wide_runs > 0 else 0

    def is_valid_delivery(self):
        if (self.wide_runs + self.no_ball_runs) == 0:
            return True
        return False

    @classmethod
    def parse(cls, score_text: str):
        if score_text == ".":
            return Score.from_tuple(0, 0, 0, 0, 0, 0, 0)
        if score_text == "W":
            return Score.from_tuple(0, 0, 0, 0, 0, 0, 1)
        if score_text == "w":
            return Score.from_tuple(0, 1, 0, 0, 0, 0, 0)
        groups = cls.SCORE_PATTERN.search(score_text)
        try:
            runs_scored = int(groups.group("num"))
        except TypeError:
            raise ValueError(f"invalid score text {score_text}")
        modifier = groups.group("mod")
        runs_off_bat = runs_scored
        if modifier:
            if modifier == "W":
                return Score.from_tuple(runs_off_bat, 0, 0, 0, 0, 0, 1)
            elif modifier == "w":
                return Score.from_tuple(0, runs_scored, 0, 0, 0, 0, 0)
            elif modifier == "nb":
                runs_off_bat -= 1
                return Score.from_tuple(runs_off_bat, 0, 0, 0, 1, 0, 0)
            elif modifier == "b":
                return Score.from_tuple(0, 0, 0, runs_scored, 0, 0, 0)
            elif modifier == "lb":
                return Score.from_tuple(0, 0, runs_scored, 0, 0, 0, 0)
            else:
                raise ValueError(f"Unknown modifier: {modifier}")
        else:
            return Score.from_tuple(runs_off_bat, 0, 0, 0, 0, 0, 0)

    def add(self, new_score):
        self.runs_off_bat += new_score.runs_off_bat
        self.wide_runs += new_score.wide_runs
        self.wide_deliveries += new_score.wide_deliveries
        self.valid_deliveries += new_score.valid_deliveries
        self.leg_byes += new_score.leg_byes
        self.byes += new_score.byes
        self.no_ball_runs += new_score.no_ball_runs
        self.penalty_runs += new_score.penalty_runs
        self.wickets += new_score.wickets
        return self

    def get_ran_runs(self):
        return self.runs_off_bat + self.byes + self.leg_byes

    def get_total_runs(self):
        return (
            self.runs_off_bat
            + self.wide_runs
            + self.leg_byes
            + self.byes
            + self.penalty_runs
            + self.no_ball_runs
        )

    def get_extra_runs(self):
        return self.leg_byes + self.byes + self.wide_runs + self.no_ball_runs

    def get_bowler_extras(self):
        return self.wide_runs + self.no_ball_runs + self.penalty_runs


class Scoreable(abc.ABC):
    def __init__(self):
        self._ball_events = []
        self._score = Score(0, 0, 0, 0, 0, 0, 0)

    @abc.abstractmethod
    def on_ball_completed(self, bce: "BallCompletedEvent"):
        pass

    def update_score(self, bce: "BallCompletedEvent"):
        self._ball_events.append(bce)
        self._score.add(bce.ball_score)

    def get_previous_ball(self):
        if len(self._ball_events) == 0:
            return None
        return self._ball_events[-1]

    def runs_scored(self) -> int:
        return self._score.runs_off_bat
