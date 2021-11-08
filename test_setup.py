import itertools

import pytest

import match_type
from match import Match
from registrar import FixedDataRegistrar, NameableType
from mux import MatchMux
import score


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


def test_registrar():
    registrar = FixedDataRegistrar()
    test_names = test_players_home
    line_up = []
    for name in test_names:
        line_up.append(registrar.create_player(name))
    team_one = registrar.create_team(test_team_home, line_up)
    assert line_up[0] is registrar.get_fixed_data(NameableType.PLAYER, test_names[0])
    assert team_one is registrar.get_fixed_data(NameableType.TEAM, test_team_home)


def test_unique_id(registrar):
    all_ids = set()
    num_items = 0
    for fixed_data in itertools.chain.from_iterable(registrar._store.values()):
        all_ids.add(fixed_data.unique_id)
        num_items += 1
    assert len(all_ids) == num_items


def test_new_match(mux, registrar):
    test_payload = {"match_type": "T",
                    "home_team": test_team_home,
                    "away_team": test_team_away,
                    "home_line_up": test_players_home,
                    "away_line_up": test_players_away}
    new_match_message = {"event_type": 0, "payload": test_payload}
    mux.on_event(new_match_message)
    assert mux.current_match.get_max_overs() == 20
    assert mux.current_match.home_team.name == test_team_home


def test_new_innings(mux, registrar):
    mock_match = MockMatch()
    teams = registrar.get_all_of_type(NameableType.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = test_players_away[-1]
    payload = {"batting_team": test_team_home, "opening_bowler": bowler_name}
    mock_match.on_new_innings(payload, registrar)
    assert mock_match.get_num_innings() == 1
    current_innings = mock_match.get_current_innings()
    assert current_innings.innings_id == 0
    assert current_innings.get_current_over().over_number == 0


def scores_match(score_one, score_two):
    if score_one.runs_off_bat != score_two.runs_off_bat:
        return False
    if score_one.wide_runs != score_two.wide_runs:
        return False
    if score_one.wide_deliveries != score_two.wide_deliveries:
        return False
    if score_one.valid_deliveries != score_two.valid_deliveries:
        return False
    if score_one.leg_byes != score_two.leg_byes:
        return False
    if score_one.byes != score_two.byes:
        return False
    if score_one.no_ball_runs != score_two.no_ball_runs:
        return False
    if score_one.penalty_runs != score_two.penalty_runs:
        return False
    if score_one.wickets != score_two.wickets:
        return False
    return True


@pytest.mark.parametrize("test_input,expected",
                         [(".", score.DOT_BALL),
                          ("w", score.WIDE_BALL),
                          ("W", score.WICKET_BALL),
                          ("1", score.Score(1, 0, 0, 0, 0, 0, 0)),
                          ("4lb", score.Score(0, 0, 4, 0, 0, 0, 0))])
def test_score_parser(test_input, expected):
    assert scores_match(score.Score.parse(test_input), expected)
