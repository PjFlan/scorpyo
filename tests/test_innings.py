from copy import deepcopy

import pytest

from scorpyo.innings import Innings, InningsState, BatterInningsState
from scorpyo.match import Match
from scorpyo.registrar import FixedDataRegistrar
from .static import HOME_PLAYERS
from .common import apply_ball_events


def test_ball_completed(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    event = mock_innings.handle_ball_completed(payload)
    assert event.ball_score.runs_off_bat == 1
    assert mock_innings.off_strike_innings.get_runs_scored() == 1
    assert mock_innings.on_strike_innings.get_runs_scored() == 0


def test_strike_rotates(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    event = mock_innings.handle_ball_completed(payload)
    assert event.players_crossed
    assert event.ball_score.runs_off_bat == 1
    expected_on_strike = HOME_PLAYERS[1]
    assert mock_innings.striker == expected_on_strike
    assert mock_innings.off_strike_innings.get_runs_scored() == 1
    assert mock_innings.on_strike_innings.get_runs_scored() == 0
    payload = {"score_text": "1"}
    mock_innings.handle_ball_completed(payload)
    expected_on_strike = HOME_PLAYERS[0]
    assert mock_innings.striker == expected_on_strike
    payload = {"score_text": "2"}
    mock_innings.handle_ball_completed(payload)
    assert mock_innings.striker == expected_on_strike


def test_multiple_deliveries(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [{"score_text": "1"}, {"score_text": "2"}, {"score_text": "."}]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.off_strike_innings.get_runs_scored() == 1
    assert mock_innings.on_strike_innings.get_runs_scored() == 2
    assert mock_innings.bowler_innings.runs_against() == 3


def test_balls_faced_bowled(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [
        {"score_text": "1"},
        {"score_text": "2"},
        {"score_text": "1lb"},
        {"score_text": "2lb"},
        {"score_text": "2w"},
    ]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.on_strike_innings.balls_faced() == 2
    assert mock_innings.off_strike_innings.balls_faced() == 2
    assert mock_innings.bowler_innings.get_balls_bowled() == 4


def test_innings_completed_all_out(
    mock_match: Match, mock_innings: Innings, registrar: FixedDataRegistrar
):
    # TODO pflanagan: theres a lot of boilerplate here needed to take wickets
    # maybe I should instead patch various methods on my mock class to do this for me
    num_batters = len(mock_innings.batting_team)
    batters_at_create = [mock_innings.non_striker.name]
    next_to_dismiss = mock_innings.on_strike_innings
    for i in range(2, num_batters - 1):
        template_innings = deepcopy(mock_innings.on_strike_innings)
        template_innings.player = mock_innings.batting_team.batter_by_position(i)
        mock_innings.batter_inningses.append(template_innings)
        mock_innings.on_strike_innings = template_innings
        next_to_dismiss.batting_state = BatterInningsState.DISMISSED
        next_to_dismiss = template_innings
    batters_at_create.append(template_innings.player.name)
    expected_ytb = [mock_innings.batting_team.batter_by_position(num_batters - 1)]
    actual_atc = [i.player.name for i in mock_innings.active_batter_innings]
    assert set(mock_innings.yet_to_bat) == set(expected_ytb)
    assert set(batters_at_create) == set(actual_atc)
    payload = {"innings_num": 0, "reason": InningsState.ALL_OUT}
    with pytest.raises(AssertionError) as exc:
        mock_match.handle_innings_completed(payload)
        exc.match(r"there are still batters remaining")
