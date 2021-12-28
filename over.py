from events import BallCompletedEvent
from player import Player
from score import Scoreable


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

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
