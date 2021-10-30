from collections import namedtuple

MatchType = namedtuple("MatchType", "innings overs")

TWENTY_20 = MatchType(1, 20)
ONE_DAY = MatchType(1, 50)

match_types = {"T": TWENTY_20,
               "O": ONE_DAY}


def get_match_type(shortcode: str):
    return match_types[shortcode]
