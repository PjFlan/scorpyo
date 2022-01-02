from copy import deepcopy

import pytest

from scorpyo.context import Context
from scorpyo.engine import MatchEngine
from scorpyo.innings import find_innings, BatterInningsState
from scorpyo.match import Match
from scorpyo.over import OverState
from scorpyo.player import Player
from scorpyo.registrar import FixedDataRegistrar, Entity
from scorpyo.static_data import match
from .static import HOME_TEAM, AWAY_TEAM, HOME_PLAYERS, AWAY_PLAYERS


# TODO: maybe these player names should be enums
test_players_home = HOME_PLAYERS
test_players_away = AWAY_PLAYERS
test_team_home = HOME_TEAM
test_team_away = AWAY_TEAM


# noinspection PyMissingConstructor
class MockMatch(Match):
    def __init__(self):
        self.match_id = 12345
        self.num_innings_completed = 0
        self.match_inningses = []
        self.match_type = match.TWENTY_20

    def swap_batters(self, old_batter, new_batter):
        existing_innings = find_innings(
            old_batter, self.current_innings.batter_inningses
        )
        new_innings = deepcopy(existing_innings)
        new_innings.batting_state = BatterInningsState.IN_PROGRESS
        existing_innings.batting_state = BatterInningsState.DISMISSED
        new_innings.player = new_batter
        self.current_innings.batter_inningses.append(new_innings)
        if self.current_innings.on_strike_innings.player == old_batter:
            self.current_innings.on_strike_innings = new_innings
        else:
            self.current_innings.off_strike_innings = new_innings

    def apply_over(self, bowler: Player):
        prev_over = self.current_innings.overs[-1]
        if prev_over.state != OverState.IN_PROGRESS:
            next_over = deepcopy(prev_over)
            next_over.state = OverState.IN_PROGRESS
            next_over.bowler = bowler
            self.current_innings.overs.append(next_over)
            next_over.state = OverState.COMPLETED
        else:
            payload = {"score_text": "."}
            self.current_innings.current_over.bowler = bowler
            for _ in range(6):
                self.current_innings.handle_ball_completed(payload)
            oc_payload = {"bowler": bowler.name, "reason": OverState.COMPLETED}
            self.current_innings.handle_over_completed(oc_payload)

    def apply_overs(self, num_overs) -> Player:
        bowling_team = self.current_innings.bowling_team
        for over in range(num_overs):
            next_idx = over % len(bowling_team)
            next_bowler = bowling_team[next_idx]
            self.apply_over(next_bowler)
        next_bowler = bowling_team[(next_idx + 1) % len(bowling_team)]
        return next_bowler


@pytest.fixture()
def registrar():
    registrar = FixedDataRegistrar()
    line_up_home = []
    line_up_away = []
    for name in test_players_home:
        line_up_home.append(registrar.create_player(name))
    for name in test_players_away:
        line_up_away.append(registrar.create_player(name))
    registrar.create_team(test_team_home, line_up_home)
    registrar.create_team(test_team_away, line_up_away)
    Context.set_fd_registrar(registrar)
    return registrar


@pytest.fixture()
def mock_engine(registrar):
    return MatchEngine()


@pytest.fixture()
def mock_match(registrar):
    return MockMatch()


@pytest.fixture()
def mock_innings(mock_match, registrar):
    teams = registrar.get_all_of_type(Entity.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = test_players_away[-1]
    payload = {"batting_team": test_team_home, "opening_bowler": bowler_name}
    mock_match.handle_innings_started(payload)
    return mock_match.current_innings
