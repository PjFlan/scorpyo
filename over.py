from player import Player
import util


class Over(util.Scoreable):
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

    def on_ball_completed(self, ball_completed_event):
        super().on_ball_completed(ball_completed_event)
        if ball_completed_event.players_crossed:
            self.on_strike, self.off_strike = util.switch_strike(
                self.on_strike, self.off_strike
            )
