from typing import NamedTuple

from score import Scoreable


class MatchType(NamedTuple):
    innings: int
    overs: int


TWENTY_20 = MatchType(1, 20)
ONE_DAY = MatchType(1, 50)

match_types = {"T": TWENTY_20, "O": ONE_DAY}


def get_match_type(shortcode: str):
    return match_types[shortcode]
