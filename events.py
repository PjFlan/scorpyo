from enum import Enum
from typing import NamedTuple

from dismissal import Dismissal
from over import Over
from static_data.match import MatchType
from player import Player
from score import Score
from team import Team


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


class InningsStartedEvent(NamedTuple):
    innings_id: int
    start_time: float
    batting_team: Team
    bowling_team: Team
    opening_bowler: Player


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
