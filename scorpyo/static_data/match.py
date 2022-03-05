from typing import NamedTuple


class MatchType(NamedTuple):
    innings_per_side: int
    overs: int
    days: int
    bowler_limit: int
    name: str


TWENTY_20 = MatchType(1, 20, 1, 4, "T20")
ONE_DAY = MatchType(1, 50, 1, 10, "ONE DAY")
FIRST_CLASS = MatchType(2, None, 4, None, "FIRST CLASS")

_match_types = {"T20": TWENTY_20, "OD": ONE_DAY, "FC": FIRST_CLASS}


def get_match_type(shortcode: str):
    if shortcode not in _match_types:
        raise ValueError(f"invalid match type {shortcode}")
    return _match_types[shortcode]
