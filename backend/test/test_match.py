from copy import deepcopy

from scorpyo.event import InningsStartedEvent
from scorpyo.innings import Innings
from scorpyo.registrar import EntityRegistrar
from scorpyo.definitions.match import FIRST_CLASS
from test.conftest import MockMatch


def test_match_target_single_innings(mock_match: MockMatch, mock_innings: Innings):
    mock_innings._score.runs_off_bat = 220
    mock_match.num_innings_completed += 1
    new_innings = deepcopy(mock_innings)
    new_innings.bowling_team = mock_innings.batting_team
    new_innings.batting_team = mock_innings.bowling_team
    new_innings.target = mock_match.next_innings_target
    new_innings._score.runs_off_bat = 0
    mock_match.match_inningses.append(new_innings)
    mock_match.num_innings_completed += 1
    assert new_innings.target == 221
    new_innings._score.runs_off_bat = 222
    assert new_innings.target_reached


def test_match_target_two_innings(mock_match: MockMatch, mock_innings: Innings):
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
    prev_innings = new_innings
    # pflanagan: we index innings numbers from 0, so 1 is the second batting innings
    ise = InningsStartedEvent(
        3,
        1,
        None,
        prev_innings.bowling_lineup,
        prev_innings.batting_lineup,
    )
    mock_match.on_innings_started(ise)
    assert mock_match.get_team_runs(mock_innings.batting_team, 0) == 220
    assert mock_match.current_innings.target == 71


def test_match_target_win_by_an_innings(mock_match: MockMatch, mock_innings: Innings):
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
    assert mock_match.next_innings_target == 0


def test_match_target_follow_on(mock_match: MockMatch, mock_innings: Innings):
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
    assert mock_match.next_innings_target == 51
