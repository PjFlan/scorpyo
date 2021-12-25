from events import BallCompletedEvent
from player import Player
from score import Scoreable
import util


class Over(Scoreable):
    def __init__(
        self,
        innings_id: int,
        over_number: int,
        on_strike: Player,
        off_strike: Player,
        bowler: Player,
    ):
        super().__init__()
        self.innings_id = innings_id
        self.over_number = over_number
        self.on_strike = on_strike
        self.off_strike = off_strike
        self.bowler = bowler

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
        if bce.players_crossed:
            # TODO: we already calculate this further upstream
            # probably safer to propagate that state somehow
            # maybe the over just stores a reference to the innings
            # which tracks all relevant state
            self.on_strike, self.off_strike = util.switch_strike(
                self.on_strike, self.off_strike
            )
