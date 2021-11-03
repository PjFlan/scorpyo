from player import Player


class Over:

    def __init__(self,
                 innings_id: int,
                 over_number: int,
                 on_strike: Player,
                 off_strike: Player,
                 bowler: Player):

        self.innings_id = innings_id
        self.over_number = over_number
        self.on_strike = on_strike
        self.off_strike = off_strike
        self.bowler = bowler
