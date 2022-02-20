from __future__ import annotations

from enum import Enum

from scorpyo.context import Context
from scorpyo.player import Player
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
        self.over_number = over_number
        self.bowler = bowler
        self.state = OverState.IN_PROGRESS

    def snapshot(self) -> dict:
        # return runs, boundaries, wickets
        return {}

    def status(self) -> dict:
        output = {
            "over_num": self.over_number,
            "bowler": self.bowler.name,
            "snapshot": self.snapshot(),
        }
        return output

    def on_ball_completed(self, bce: "BallCompletedEvent"):
        super().update_score(bce)

    def on_over_completed(self, oc: "OverCompletedEvent"):
        assert self.over_number == oc.number, "OverCompletedEvent raised for wrong over"
        self.state = OverState.COMPLETED
