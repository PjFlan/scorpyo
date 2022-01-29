from copy import deepcopy

from scorpyo.innings import Innings
from scorpyo.registrar import EntityRegistrar
from scorpyo.static_data.match import FIRST_CLASS
from tests.conftest import MockMatch


def test_match_target_single_innings(
    mock_match: MockMatch, mock_innings: Innings, registrar: EntityRegistrar
):
    mock_innings._score.runs_off_bat = 220
    assert mock_match.target is None
    mock_match.num_innings_completed += 1
    new_innings = deepcopy(mock_innings)
    new_innings.bowling_team = mock_innings.batting_team
    new_innings.batting_team = mock_innings.bowling_team
    new_innings._score.runs_off_bat = 0
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target == 221
    new_innings._score.runs_off_bat = 222
    assert mock_match.target_reached


def test_match_target_two_innings(
    mock_match: MockMatch, mock_innings: Innings, registrar: EntityRegistrar
):
    mock_match.match_type = FIRST_CLASS
    mock_innings._score.runs_off_bat = 220
    assert mock_match.target is None
    mock_match.num_innings_completed += 1
    new_innings = deepcopy(mock_innings)
    new_innings.bowling_team = mock_innings.batting_team
    new_innings.batting_team = mock_innings.bowling_team
    new_innings._score.runs_off_bat = 300
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target is None
    new_innings = deepcopy(mock_innings)
    new_innings._score.runs_off_bat = 150
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.get_team_runs(mock_innings.batting_team, 0) == 220
    assert mock_match.target == 71


def test_match_target_win_by_an_innings(
    mock_match: MockMatch, mock_innings: Innings, registrar: EntityRegistrar
):
    mock_match.match_type = FIRST_CLASS
    mock_innings._score.runs_off_bat = 400
    assert mock_match.target is None
    mock_match.num_innings_completed += 1
    new_innings = deepcopy(mock_innings)
    new_innings.bowling_team = mock_innings.batting_team
    new_innings.batting_team = mock_innings.bowling_team
    new_innings._score.runs_off_bat = 100
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target is None
    new_innings = deepcopy(new_innings)
    new_innings._score.runs_off_bat = 150
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target_reached


def test_match_target_follow_on(
    mock_match: MockMatch, mock_innings: Innings, registrar: EntityRegistrar
):
    mock_match.match_type = FIRST_CLASS
    mock_innings._score.runs_off_bat = 400
    assert mock_match.target is None
    mock_match.num_innings_completed += 1
    new_innings = deepcopy(mock_innings)
    new_innings.bowling_team = mock_innings.batting_team
    new_innings.batting_team = mock_innings.bowling_team
    new_innings._score.runs_off_bat = 100
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target is None
    new_innings = deepcopy(new_innings)
    new_innings._score.runs_off_bat = 350
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert mock_match.target_reached is False
    assert mock_match.target == 51