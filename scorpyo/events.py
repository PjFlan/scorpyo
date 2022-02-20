from enum import Enum
from typing import NamedTuple

from scorpyo.dismissal import Dismissal
from scorpyo.static_data.match import MatchType
from scorpyo.player import Player
from scorpyo.score import Score
from scorpyo.team import Team, MatchTeam


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
    REGISTER_LINE_UP = 10


class EventMessageType(Enum):
    """not exactly a one-to-one mapping of EventType (which is a little confusing)"""

    # TODO pflanagan: at the moment we have no corresponding class for each of these
    #  types and the message is just a python dict. In future should solidify the
    #  interfaces
    MATCH_STARTED = 0
    MATCH_COMPLETED = 1
    INNINGS_STARTED = 2
    INNINGS_COMPLETED = 3
    OVER_STARTED = 4
    OVER_COMPLETED = 5
    BATTER_INNINGS_STARTED = 6
    BATTER_INNINGS_COMPLETED = 7
    INNINGS_UPDATE = 8


class MatchStartedEvent(NamedTuple):
    match_id: int
    match_type: MatchType
    start_time: float
    home_team: Team
    away_team: Team
    event_message = EventMessageType.MATCH_STARTED


class MatchCompletedEvent(NamedTuple):
    match_id: int
    end_time: float
    reason: "MatchState"
    event_message = EventMessageType.MATCH_COMPLETED


class InningsStartedEvent(NamedTuple):
    match_innings_num: int
    batting_team_innings_num: int
    start_time: float
    batting_lineup: MatchTeam
    bowling_lineup: MatchTeam
    opening_bowler: Player
    event_message = EventMessageType.INNINGS_UPDATE


class InningsCompletedEvent(NamedTuple):
    match_innings_num: int
    end_time: float
    reason: "InningsState"
    event_message = EventMessageType.INNINGS_COMPLETED


class BallCompletedEvent(NamedTuple):
    on_strike_player: Player
    off_strike_player: Player
    bowler: Player
    ball_score: Score
    players_crossed: bool
    dismissal: Dismissal
    event_message = EventMessageType.INNINGS_UPDATE


class BatterInningsCompletedEvent(NamedTuple):
    batter: Player
    batting_state: "BatterInningsState"
    event_message = EventMessageType.BATTER_INNINGS_COMPLETED


class BatterInningsStartedEvent(NamedTuple):
    batter: Player
    event_message = EventMessageType.INNINGS_STARTED


class OverCompletedEvent(NamedTuple):
    number: int
    bowler: Player
    reason: "OverState"
    event_message = EventMessageType.OVER_COMPLETED


class OverStartedEvent(NamedTuple):
    bowler: Player
    over_number: int
    event_message = EventMessageType.INNINGS_STARTED
