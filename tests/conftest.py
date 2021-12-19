import pytest

import match_type
from match import Match
from mux import MatchMux
from registrar import FixedDataRegistrar, Nameable

test_players_home = ["Padraic Flanagan", "Jack Tector", "Harry Tector", "Bobby Gamble"]
test_players_away = ["JJ Cassidy", "Callum Donnelly", "Tim Tector", "Oliver Gunning"]
test_team_home = "YMCA CC"
test_team_away = "Pembroke CC"


# noinspection PyMissingConstructor
class MockMatch(Match):
    def __init__(self):
        self.match_id = 12345
        self.match_inningses = []
        self.match_type = match_type.TWENTY_20


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
    return registrar


@pytest.fixture()
def mux(registrar):
    return MatchMux(registrar)


@pytest.fixture()
def mock_match():
    return MockMatch()


@pytest.fixture()
def mock_innings(registrar):
    mock_match = MockMatch()
    teams = registrar.get_all_of_type(Nameable.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = test_players_away[-1]
    payload = {"batting_team": test_team_home, "opening_bowler": bowler_name}
    mock_match.on_new_innings(payload, registrar)
    return mock_match.get_current_innings()
