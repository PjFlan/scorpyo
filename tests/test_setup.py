import itertools

from scorpyo.registrar import FixedDataRegistrar, Entity
from .static import HOME_TEAM, AWAY_TEAM, HOME_PLAYERS, AWAY_PLAYERS


def test_registrar():
    registrar = FixedDataRegistrar()
    test_names = HOME_PLAYERS
    test_team_home = HOME_TEAM
    line_up = []
    for name in test_names:
        line_up.append(registrar.create_player(name))
    team_one = registrar.create_team(test_team_home, line_up)
    assert line_up[0] is registrar.get_fixed_data(Entity.PLAYER, test_names[0])
    assert team_one is registrar.get_fixed_data(Entity.TEAM, test_team_home)


def test_unique_id(registrar):
    all_ids = set()
    num_items = 0
    for fixed_data in itertools.chain.from_iterable(registrar._store.values()):
        all_ids.add(fixed_data.unique_id)
        num_items += 1
    assert len(all_ids) == num_items


def test_new_match(mock_engine, registrar):
    test_payload = {
        "match_type": "T",
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
        "home_line_up": HOME_PLAYERS,
        "away_line_up": AWAY_PLAYERS,
    }
    new_match_message = {"event_type": 0, "payload": test_payload}
    mock_engine.on_event(new_match_message)
    assert mock_engine.current_match.max_overs == 20
    assert mock_engine.current_match.home_team.name == HOME_TEAM


def test_new_innings(registrar, mock_match):
    teams = registrar.get_all_of_type(Entity.TEAM)
    mock_match.home_team = teams[0]
    mock_match.away_team = teams[1]
    bowler_name = AWAY_PLAYERS[-1]
    payload = {"batting_team": HOME_TEAM, "opening_bowler": bowler_name}
    mock_match.handle_innings_started(payload)
    assert len(mock_match.match_inningses) == 1
    current_innings = mock_match.current_innings
    assert current_innings.innings_num == 0
    assert current_innings.current_over.over_number == 0
