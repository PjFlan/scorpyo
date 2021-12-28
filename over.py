from __future__ import annotations

from enum import Enum

from player import Player
from score import Scoreable


class OverState(Enum):
    IN_PROGRESS = "ip"
    COMPLETED = "c"
    INNINGS_ENDED = "ie"


class Over(Scoreable):
    def __init__(
        self,
        over_number: int,
        bowler: Player,
        innings: "Innings",
    ):
        super().__init__()
        self.innings = innings
        self.over_number = over_number
        self.bowler = bowler
        self.state = OverState.IN_PROGRESS

    def on_ball_completed(self, bce: "BallCompletedEvent"):
        super().update_score(bce)

    def on_over_completed(self, oc: "OverCompletedEvent"):
        self.state = OverState.COMPLETED
