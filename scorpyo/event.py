from enum import Enum
from functools import wraps
from typing import NamedTuple

from scorpyo.dismissal import Dismissal
from scorpyo.static_data.match import MatchType
from scorpyo.entity import Player
from scorpyo.score import Score
from scorpyo.entity import Team, MatchTeam


class EventType(Enum):
    MATCH_STARTED = "ms"
    INNINGS_STARTED = "is"
    BALL_COMPLETED = "bc"
    OVER_STARTED = "os"
    OVER_COMPLETED = "oc"
    INNINGS_COMPLETED = "ic"
    MATCH_COMPLETED = "mc"
    BATTER_INNINGS_COMPLETED = "bic"
    BATTER_INNINGS_STARTED = "bis"
    REGISTER_LINE_UP = "rlu"


class MatchStartedEvent(NamedTuple):
    match_id: int
    match_type: MatchType
    start_time: float
    home_team: Team
    away_team: Team


class MatchCompletedEvent(NamedTuple):
    match_id: int
    end_time: float
    reason: "MatchState"


class InningsStartedEvent(NamedTuple):
    match_innings_num: int
    batting_team_innings_num: int
    start_time: float
    batting_lineup: MatchTeam
    bowling_lineup: MatchTeam
    opening_bowler: Player


class InningsCompletedEvent(NamedTuple):
    match_innings_num: int
    end_time: float
    reason: "InningsState"


class BallCompletedEvent(NamedTuple):
    on_strike_player: Player
    off_strike_player: Player
    bowler: Player
    ball_score: Score
    players_crossed: bool
    dismissal: Dismissal


class BatterInningsCompletedEvent(NamedTuple):
    batter: Player
    batting_state: "BatterInningsState"


class BatterInningsStartedEvent(NamedTuple):
    batter: Player


class OverCompletedEvent(NamedTuple):
    number: int
    bowler: Player
    reason: "OverState"


class OverStartedEvent(NamedTuple):
    bowler: Player
    number: int


class RegisterTeamLineup(NamedTuple):
    lineup: list[Player]


def record_event(func: callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        obj = args[0]  # self
        obj.event_registrar.add(args[1])
        return func(*args, **kwargs)

    return wrapper
