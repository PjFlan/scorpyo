from dataclasses import dataclass
from enum import Enum
from functools import wraps

from scorpyo.dismissal import Dismissal
from scorpyo.definitions.match import MatchType
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
    REJECT = "rj"


@dataclass
class MatchStartedEvent:
    match_id: int
    match_type: MatchType
    start_time: float
    home_team: Team
    away_team: Team


@dataclass
class MatchCompletedEvent:
    match_id: int
    end_time: float
    reason: "MatchState"


@dataclass
class InningsStartedEvent:
    match_innings_num: int
    batting_team_innings_num: int
    start_time: float
    batting_lineup: MatchTeam
    bowling_lineup: MatchTeam


@dataclass
class InningsCompletedEvent:
    match_innings_num: int
    end_time: float
    reason: "InningsState"


@dataclass
class BallCompletedEvent:
    on_strike_player: Player
    off_strike_player: Player
    bowler: Player
    ball_score: Score
    players_crossed: bool
    dismissal: Dismissal


@dataclass
class BatterInningsCompletedEvent:
    batter: Player
    batting_state: "BatterInningsState"


@dataclass
class BatterInningsStartedEvent:
    batter: Player


@dataclass
class OverCompletedEvent:
    number: int
    bowler: Player
    reason: "OverState"


@dataclass
class OverStartedEvent:
    bowler: Player
    number: int


@dataclass
class RegisterTeamLineup:
    lineup: list[Player]


def record_command(func: callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        obj = args[0]  # self
        obj.command_registrar.add(args[1])
        return func(*args, **kwargs)

    return wrapper
