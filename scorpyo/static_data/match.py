from typing import NamedTuple


class MatchType(NamedTuple):
    innings_per_side: int
    overs: int
    bowler_limit: int


TWENTY_20 = MatchType(1, 20, 4)
ONE_DAY = MatchType(1, 50, 10)

_match_types = {"T": TWENTY_20, "O": ONE_DAY}


def get_match_type(shortcode: str):
    return _match_types[shortcode]
