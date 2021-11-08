import time
from enum import Enum

from innings import Innings
from match_type import MatchType, get_match_type
from player import Player
from score import Score
from team import Team
from registrar import FixedDataRegistrar, NameableType


class EventType(Enum):
    MATCH_STARTED = 0
    MATCH_TEAM_ADDED = 1
    INNINGS_STARTED = 2
    BALL_COMPLETED = 3
    OVER_STARTED = 4
    OVER_COMPLETED = 5
    INNINGS_COMPLETED = 6
    MATCH_COMPLETED = 7


class MatchStartedEvent:

    def __init__(self,
                 match_id: int,
                 match_type: MatchType,
                 start_time: float,
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
        start_time = get_current_time()
        match_type = get_match_type(payload["match_type"])
        match_id = int(start_time)
        home_team = registrar.get_fixed_data(NameableType.TEAM, payload["home_team"])
        away_team = registrar.get_fixed_data(NameableType.TEAM, payload["away_team"])
        home_team.add_line_up(registrar.get_from_names(NameableType.PLAYER,
                                                       payload["home_line_up"]))
        away_team.add_line_up(registrar.get_from_names(NameableType.PLAYER,
                                                       payload["away_line_up"]))
        return cls(match_id, match_type, start_time, home_team, away_team)


class InningsStartedEvent:

    def __init__(self, innings_id: int, start_time: float, batting_team: Team,
                 bowling_team: Team, opening_bowler: Player):
        self.innings_id = innings_id
        self.start_time = start_time
        self.batting_team = batting_team
        self.bowling_team = bowling_team
        self.opening_bowler = opening_bowler

    @classmethod
    def build(cls, payload: dict, registrar: FixedDataRegistrar, match):
        start_time = get_current_time()
        innings_id = match.get_num_innings()  # index innings from 0 not 1
        batting_team = registrar.get_fixed_data(NameableType.TEAM,
                                                payload["batting_team"])
        bowling_team = [team for team in match.get_teams() if team != batting_team][0]
        opening_bowler = registrar.get_fixed_data(NameableType.PLAYER,
                                                  payload["opening_bowler"])
        return cls(innings_id, start_time, batting_team, bowling_team, opening_bowler)


class BallCompletedEvent:

    def __init__(self, on_strike, off_strike, bowler, ball_score, ball_in_over_number,
                 ball_in_innings_number, players_crossed):
        self.on_strike = on_strike
        self.off_strike = off_strike
        self.bowler = bowler
        self.ball_score = ball_score
        self.ball_in_over_number = ball_in_over_number
        self.ball_in_innings_number = ball_in_innings_number
        self.players_crossed = players_crossed

    @classmethod
    def build(cls, payload: dict, current_innings: Innings):
        ball_score = Score.parse(payload["score_text"])
        prev_ball_event = current_innings.get_previous_ball()
        ball_increment = 1 if ball_score.is_valid_delivery() else 0
        ball_in_over_number = prev_ball_event.ball_in_over_number + ball_increment
        ball_in_innings_number = prev_ball_event.ball_in_innings_number + ball_increment
        striker = current_innings.on_strike
        non_striker = current_innings.off_strike
        bowler = current_innings.get_current_bowler()
        players_crossed = False
        if ball_score.wide_runs > 0 and ball_score.wide_runs % 2 == 0:
            players_crossed = True
        elif ball_score.get_ran_runs() % 2 == 1:
            players_crossed = True
        ball_completed_event = BallCompletedEvent(striker,
                                                  non_striker,
                                                  bowler,
                                                  ball_score,
                                                  ball_in_over_number,
                                                  ball_in_innings_number,
                                                  players_crossed)
        return ball_completed_event


def get_current_time():
    return time.time()
