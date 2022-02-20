from enum import Enum
from typing import NamedTuple

from scorpyo.dismissal import Dismissal
from scorpyo.static_data.match import MatchType
from scorpyo.player import Player
from scorpyo.score import Score
from scorpyo.team import Team, MatchTeam


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


class EventMessageType(Enum):
    """not exactly a one-to-one mapping of EventType (which is a little confusing)"""

    # TODO pflanagan: at the moment we have no corresponding class for each of these
    #  types and the message is just a python dict. In future should solidify the
    #  interfaces
    MATCH_OVERVIEW = "mo"
    INNINGS_OVERVIEW = "io"
    OVER_OVERVIEW = "oo"
    BATTER_INNINGS_OVERVIEW = "baio"
    BOWLER_INNINGS_OVERVIEW = "boio"
    INNINGS_UPDATE = "iu"
    MATCH_TEAM_OVERVIEW = "mto"


class MatchStartedEvent(NamedTuple):
    match_id: int
    match_type: MatchType
    start_time: float
    home_team: Team
    away_team: Team
    event_message = EventMessageType.MATCH_OVERVIEW


class MatchCompletedEvent(NamedTuple):
    match_id: int
    end_time: float
    reason: "MatchState"
    event_message = EventMessageType.MATCH_OVERVIEW


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
    event_message = EventMessageType.INNINGS_OVERVIEW


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
    event_message = EventMessageType.BATTER_INNINGS_OVERVIEW


class BatterInningsStartedEvent(NamedTuple):
    batter: Player
    event_message = EventMessageType.INNINGS_OVERVIEW


class OverCompletedEvent(NamedTuple):
    number: int
    bowler: Player
    reason: "OverState"
    event_message = EventMessageType.OVER_OVERVIEW


class OverStartedEvent(NamedTuple):
    bowler: Player
    over_number: int
    event_message = EventMessageType.INNINGS_OVERVIEW


class RegisterTeamLineup(NamedTuple):
    lineup: list[Player]
    event_message = EventMessageType.MATCH_TEAM_OVERVIEW
