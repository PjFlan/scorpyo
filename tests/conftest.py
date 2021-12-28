import pytest

from context import Context
from engine import MatchEngine
from match import Match
from registrar import FixedDataRegistrar, Entities
import static_data.match as match
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
        self.match_inningses = []
        self.match_type = match.TWENTY_20


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
def mux(registrar):
    return MatchEngine()


@pytest.fixture()
def mock_match():
    return MockMatch()


@pytest.fixture()
def mock_innings(registrar):
    mock_match = MockMatch()
    teams = registrar.get_all_of_type(Entities.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = test_players_away[-1]
    payload = {"batting_team": test_team_home, "opening_bowler": bowler_name}
    mock_match.handle_innings_started(payload)
    return mock_match.get_current_innings()
