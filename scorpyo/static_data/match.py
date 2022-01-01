from typing import NamedTuple


class MatchType(NamedTuple):
    innings: int
    overs: int
    bowler_limit: int


TWENTY_20 = MatchType(1, 20, 4)
ONE_DAY = MatchType(1, 50, 10)

match_types = {"T": TWENTY_20, "O": ONE_DAY}


def get_match_type(shortcode: str):
    return match_types[shortcode]
