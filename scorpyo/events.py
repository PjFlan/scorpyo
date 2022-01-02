from enum import Enum
from typing import NamedTuple

from scorpyo.dismissal import Dismissal
from scorpyo.static_data.match import MatchType
from scorpyo.player import Player
from scorpyo.score import Score
from scorpyo.team import Team


class EventType(Enum):
    MATCH_STARTED = 0
    MATCH_TEAM_ADDED = 1
    INNINGS_STARTED = 2
    BALL_COMPLETED = 3
    OVER_STARTED = 4
    OVER_COMPLETED = 5
    INNINGS_COMPLETED = 6
    MATCH_COMPLETED = 7
    BATTER_INNINGS_COMPLETED = 8
    BATTER_INNINGS_STARTED = 9


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
    innings_num: int
    start_time: float
    batting_team: Team
    bowling_team: Team
    opening_bowler: Player


class InningsCompletedEvent(NamedTuple):
    innings_num: int
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
    bowler: Player
    reason: "OverState"


class OverStartedEvent(NamedTuple):
    bowler: Player
    over_number: int
