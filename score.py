import re


class Score:

    SCORE_PATTERN = re.compile("(?P<num>[0-9]+)?(?P<mod>[a-zA-Z]+)?")

    def __init__(self, runs_off_bat, wide_runs, leg_byes, byes, no_ball_runs,
                 penalty_runs, wickets):
        self.runs_off_bat = runs_off_bat
        self.wide_runs = wide_runs
        self.leg_byes = leg_byes
        self.byes = byes
        self.no_ball_runs = no_ball_runs
        self.penalty_runs = penalty_runs
        self.wickets = wickets
        self.valid_deliveries = 0
        self.wide_deliveries = 0
        self._set_calculated_data()

    def _set_calculated_data(self):
        self.valid_deliveries = int(self.is_valid_delivery())
        self.wide_deliveries = 1 if self.wide_runs > 0 else 0

    def is_valid_delivery(self):
        if (self.wide_runs + self.no_ball_runs) == 0:
            return True
        return False

    @classmethod
    def parse(cls, score_text: str):
        if score_text == ".":
            return DOT_BALL
        if score_text == "W":
            return WICKET_BALL
        if score_text == "w":
            return WIDE_BALL
        groups = cls.SCORE_PATTERN.search(score_text)
        try:
            runs_scored = int(groups.group("num"))
        except TypeError:
            raise ValueError(f"invalid score text {score_text}")
        modifier = groups.group("mod")
        runs_off_bat = runs_scored
        if modifier:
            if modifier == "W":
                return Score(runs_off_bat, 0, 0, 0, 0, 0, 1)
            elif modifier == "w":
                return Score(0, runs_scored, 0, 0, 0, 0, 0)
            elif modifier == "nb":
                runs_off_bat -= 1
                return Score(runs_off_bat, 0, 0, 0, 1, 0, 0)
            elif modifier == "b":
                return Score(0, 0, 0, runs_scored, 0, 0, 0)
            elif modifier == "lb":
                return Score(0, 0, runs_scored, 0, 0, 0, 0)
            else:
                raise ValueError(f"Unknown modifier: {modifier}")
        else:
            return Score(runs_off_bat, 0, 0, 0, 0, 0, 0)

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
        return self.runs_off_bat + self.wide_runs + self.leg_byes + self.byes + \
               self.penalty_runs + self.no_ball_runs

    def get_extra_runs(self):
        return self.leg_byes + self.byes + self.wide_runs + self.no_ball_runs


BLANK_SCORE = Score(0, 0, 0, 0, 0, 0, 0)
DOT_BALL = Score(1, 0, 0, 0, 0, 0, 0)
WICKET_BALL = Score(0, 0, 0, 0, 0, 0, 1)
WIDE_BALL = Score(0, 1, 0, 0, 0, 0, 0)
