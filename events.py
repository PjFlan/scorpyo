from datetime import datetime
import time
from enum import Enum

from match_type import MatchType, get_match_type
from team import Team
from registrar import FixedDataRegistrar, NameableType

class EventType(Enum):
    MATCH_STARTED = 0
    MATCH_TEAM_ADDED = 1
    INNINGS_STARTED = 2
    BALL_BOWLED = 3
    OVER_STARTED = 4
    OVER_COMPLETED = 5
    INNINGS_COMPLETED = 6
    MATCH_COMPLETED = 7


class MatchStartedEvent:

    def __init__(self,
                 match_id: int,
                 match_type: MatchType,
                 start_time: datetime,
                 home_team: Team,
                 away_team: Team,
                 ):
        self.match_id = match_id
        self.match_type = match_type
        self.start_time = start_time
        self.end_time = None
        self.home_team = home_team
        self.away_team = away_team

    @classmethod
    def build(cls, payload: dict, registrar: FixedDataRegistrar):
        start_time = time.time()
        match_type = get_match_type(payload["match_type"])
        match_id = start_time
        home_team = registrar.get_by_name(NameableType.TEAM, payload["home_team"])
        away_team = registrar.get_by_name(NameableType.TEAM, payload["away_team"])
        home_team.add_line_up(registrar.get_from_names(NameableType.PLAYER, payload[
                                                           "home_line_up"]))
        away_team.add_line_up(registrar.get_from_names(NameableType.PLAYER, payload[
                                                           "away_line_up"]))
        return cls(match_id, match_type, start_time, home_team, away_team)

