import itertools

import pytest

import match_type
from match import Match
from registrar import FixedDataRegistrar, NameableType
from mux import MatchMux

test_players = ["Padraic Flanagan", "Jack Tector", "Harry Tector", "Bobby Gamble"]
test_teams = ["YMCA CC", "Pembroke CC"]


# noinspection PyMissingConstructor
class MockMatch(Match):

    def __init__(self):
        self.match_id = 12345
        self.match_inningses = []
        self.match_type = match_type.TWENTY_20


@pytest.fixture()
def registrar():
    registrar = FixedDataRegistrar()
    for name in test_players:
        registrar.create_player(name)
    players = registrar.get_all_of_type(NameableType.PLAYER)
    line_up_one = players[:2]
    line_up_two = players[2:]
    registrar.create_team(test_teams[0], line_up_one)
    registrar.create_team(test_teams[1], line_up_two)
    return registrar


@pytest.fixture()
def mux(registrar):
    return MatchMux(registrar)


def test_registrar():
    registrar = FixedDataRegistrar()
    test_names = ["Padraic Flanagan", "Jack Tector"]
    player_one = registrar.create_player(test_names[0])
    player_two = registrar.create_player(test_names[1])
    line_up = [player_one, player_two]
    team_one = registrar.create_team("YMCA CC", line_up)
    assert player_one is registrar.get_fixed_data(NameableType.PLAYER, test_names[0])
    assert team_one is registrar.get_fixed_data(NameableType.TEAM, "YMCA CC")


def test_unique_id(registrar):
    all_ids = set()
    num_items = 0
    for fixed_data in itertools.chain.from_iterable(registrar._store.values()):
        all_ids.add(fixed_data.unique_id)
        num_items += 1
    assert len(all_ids) == num_items


def test_new_match(mux, registrar):
    home_line_up = test_players[:2]
    away_line_up = test_players[2:]
    home_team, away_team = test_teams[0], test_teams[1]
    test_payload = {"match_type": "T",
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_line_up": home_line_up,
                    "away_line_up": away_line_up}
    new_match_message = {"event_type": 0, "payload": test_payload}
    mux.on_event(new_match_message)
    assert mux.current_match.get_max_overs() == 20
    assert mux.current_match.home_team.name == home_team


def test_new_innings(mux, registrar):
    mock_match = MockMatch()
    teams = registrar.get_all_of_type(NameableType.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = teams[1].get_line_up()[-1].name
    payload = {"batting_team": teams[0].name, "opening_bowler": bowler_name}
    mock_match.on_new_innings(payload, registrar)
    assert mock_match.get_num_innings() == 1
    current_innings = mock_match.get_current_innings()
    assert current_innings.innings_id == 0
    assert current_innings.get_current_over().over_number == 0
