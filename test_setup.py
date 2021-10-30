import pytest

from registrar import FixedDataRegistrar, NameableType
from mux import MatchMux

test_players = ["Padraic Flanagan", "Jack Tector", "Harry Tector", "Bobbly Gamble"]
test_teams = ["YMCA CC", "Pembroke CC"]


@pytest.fixture()
def registrar():
    registrar = FixedDataRegistrar()
    for name in test_players:
        registrar.create_player(name)
    players = registrar.get_players()
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
    assert player_one is registrar.get_by_name(NameableType.PLAYER, test_names[0])
    assert team_one is registrar.get_by_name(NameableType.TEAM, "YMCA CC")


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
    assert mux.current_match.get_num_overs() == 20
    assert mux.current_match.home_team.name == home_team
