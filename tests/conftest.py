import pytest

from engine import MatchEngine
from events import InningsStartedEvent
from innings import Innings
from match import Match
from registrar import FixedDataRegistrar, Nameable
import static_data.match as match

test_players_home = ["Padraic Flanagan", "Jack Tector", "Harry Tector", "Bobby Gamble"]
test_players_away = ["JJ Cassidy", "Callum Donnelly", "Tim Tector", "Oliver Gunning"]
test_team_home = "YMCA CC"
test_team_away = "Pembroke CC"


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
    return registrar


@pytest.fixture()
def mux(registrar):
    return MatchEngine(registrar)


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
    ise = InningsStartedEvent.build(payload, registrar, mock_match)
    mock_innings = Innings(ise)
    mock_match.add_innings(mock_innings)
    return mock_match.get_current_innings()
