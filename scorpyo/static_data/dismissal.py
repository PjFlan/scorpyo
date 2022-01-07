from typing import NamedTuple


class DismissalType(NamedTuple):
    name: str
    abbrv: str
    bowler_accredited: bool
    batter_implied: bool
    needs_fielder: bool


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

_dismissal_type = {
    "b": BOWLED,
    "ct": CAUGHT,
    "lbw": LBW,
    "st": STUMPED,
    "ro": RUN_OUT,
    "hw": HIT_WICKET,
    "ht": HIT_BALL_TWICE,
    "to": TIMED_OUT,
    "hb": HANDLED_BALL,
    "of": OBSTRUCTING_FIELD,
}


def get_dismissal_type(shortcode: str):
    if shortcode not in _dismissal_type:
        raise ValueError(f"invalid dismissal type {shortcode}")
    return _dismissal_type[shortcode]
