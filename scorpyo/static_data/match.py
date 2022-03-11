from dataclasses import dataclass
from typing import NamedTuple


@dataclass
class MatchType:
    shortcode: str
    innings_per_side: int
    overs: int
    days: int
    bowler_limit: int
    name: str


TWENTY_20 = MatchType("T20", 1, 20, 1, 4, "TWENTY20")
ONE_DAY = MatchType("OD", 1, 50, 1, 10, "ONE DAY")
FIRST_CLASS = MatchType("FC", 2, None, 4, None, "FIRST CLASS")

_match_types = {"T20": TWENTY_20, "OD": ONE_DAY, "FC": FIRST_CLASS}


def get_match_type(shortcode: str) -> MatchType:
    if shortcode not in _match_types:
        raise ValueError(f"invalid match type {shortcode}")
    return _match_types[shortcode]


def get_all_shortcodes() -> list[str]:
    return _match_types.keys()


def get_all_types() -> list[MatchType]:
    return _match_types.values()
