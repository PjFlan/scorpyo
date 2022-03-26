from __future__ import annotations

from enum import Enum

from scorpyo.context import Context
from scorpyo.entity import Player
from scorpyo.score import Scoreable


class OverState(Enum):
    IN_PROGRESS = "ip"
    COMPLETED = "c"
    INNINGS_ENDED = "ie"


class Over(Context, Scoreable):
    def __init__(
        self,
        over_number: int,
        bowler: Player,
        innings: "Innings",
    ):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.innings = innings
        self.number = over_number
        self.bowler = bowler
        self.state = OverState.IN_PROGRESS

    @property
    def maiden(self) -> bool:
        if self._score.valid_deliveries < 6:
            return False
        return self._score.runs_against_bowler == 0

    @property
    def max_balls_bowled(self) -> bool:
        return self.balls_bowled == 6

    def description(self) -> dict:
        output = {"over_number": self.number + 1, "bowler": self.bowler.name}
        return output

    def snapshot(self) -> dict:
        output = {
            "total_runs": self.total_runs,
            "wides": self._score.wide_runs,
            "no_balls": self._score.no_ball_runs,
            "byes": self._score.byes,
            "leg_byes": self._score.leg_byes,
            "penalty_runs": self._score.penalty_runs,
            "wickets": self._score.wickets,
            "fours": self._score.fours,
            "sixes": self._score.sixes,
            "dots": self._score.dots,
        }
        return output

    def overview(self) -> dict:
        output = {
            "description": self.description(),
            "snapshot": self.snapshot(),
            "maiden": self.maiden,
        }
        return output

    def on_ball_completed(self, bce: "BallCompletedEvent"):
        super().update_score(bce)

    def on_over_completed(self, oce: "OverCompletedEvent"):
        assert self.number == oce.number, "OverCompletedEvent raised for wrong over"
        self.state = oce.reason
