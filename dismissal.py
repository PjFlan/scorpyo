import functools

from player import Player
from registrar import FixedDataRegistrar, NameableType


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


class Dismissal:
    def __init__(
        self,
        dismissal_type: DismissalType,
        batter: Player,
        bowler: Player,
        fielder: Player,
    ):
        self.dismissal_type = dismissal_type
        self.batter = batter
        self.bowler = bowler
        self.fielder = fielder

    @classmethod
    def parse(
        cls,
        payload: dict,
        on_strike: Player,
        off_strike: Player,
        bowler: Player,
        registrar: FixedDataRegistrar,
    ):
        dt = DismissalType.get_from_abbrv(payload["type"])
        if not dt.bowler_accredited and "bowler" in payload:
            raise ValueError(f"dismissal type {dt} should not specify a bowler")
        if not dt.batter_implied and "batter" not in payload:
            raise ValueError(f"dismissal type {dt} must specify batter")
        player_getter = functools.partial(registrar.get_fixed_data, NameableType.PLAYER)
        payload_batter = player_getter(payload.get("batter"))
        payload_bowler = player_getter(payload.get("bowler"))
        fielder = player_getter(payload.get("fielder"))
        if payload_batter and payload_batter not in [off_strike, on_strike]:
            raise ValueError(
                f"batter specified in dismissal {dt}: {payload_batter} is not "
                f"currently at the crease."
            )
        batter = payload_batter if payload_batter else on_strike
        bowler = payload_bowler if payload_bowler else bowler
        if dt.batter_implied and not batter == on_strike:
            raise ValueError(
                f"batter specified in dismissal {dt} is not consistent "
                f"with current striker: {on_strike}"
            )
        if dt.needs_fielder and not fielder:
            raise ValueError(
                f"dismissal type {dt} needs an associated fielder but "
                f"none was specified"
            )
        return Dismissal(dt, batter, bowler, fielder)

    def bowler_accredited(self):
        return self.dismissal_type.bowler_accredited
