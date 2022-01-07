# TODO pflanagan: I don't like this implementation but fine for now
class DismissalType:

    _dismissals = {}

    def __init__(
        self,
        name: str,
        abbrv: str,
        bowler_accredited: bool,
        batter_implied: bool,
        needs_fielder: True,
    ):
        self.name = name
        self.abbrv = abbrv
        self.bowler_accredited = bowler_accredited
        self.needs_fielder = needs_fielder
        self.batter_implied = batter_implied
        self._dismissals[abbrv] = self

    @classmethod
    def get_from_abbrv(cls, abbrv: str):
        return cls._dismissals[abbrv]

    def __str__(self):
        return self.name


BOWLED = DismissalType("bowled", "b", True, True, False)
CAUGHT = DismissalType("caught", "ct", True, True, True)
LBW = DismissalType("leg before wicket", "lbw", True, True, False)
STUMPED = DismissalType("stumped", "st", True, True, False)
RUN_OUT = DismissalType("run out", "ro", False, False, True)
HIT_WICKET = DismissalType("hit wicket", "hw", True, True, False)
HIT_BALL_TWICE = DismissalType("hit twice", "ht", False, True, False)
TIMED_OUT = DismissalType("timed out", "to", False, True, False)
HANDLED_BALL = DismissalType("handled ball", "hb", False, False, False)
OBSTRUCTING_FIELD = DismissalType("obstructing field", "of", False, False, False)
