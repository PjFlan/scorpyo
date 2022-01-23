from typing import NamedTuple


class MatchType(NamedTuple):
    innings_per_side: int
    overs: int
    days: int
    bowler_limit: int


TWENTY_20 = MatchType(1, 20, 1, 4)
ONE_DAY = MatchType(1, 50, 1, 10)
FIRST_CLASS = MatchType(2, None, 4, None)

_match_types = {"T20": TWENTY_20, "ODI": ONE_DAY}


def get_match_type(shortcode: str):
    if shortcode not in _match_types:
        raise ValueError(f"invalid match type {shortcode}")
    return _match_types[shortcode]
