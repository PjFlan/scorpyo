import pytest

from scorpyo.error import EngineError
from scorpyo.innings import Innings, BatterInningsState
from scorpyo.registrar import EntityRegistrar
from .common import apply_ball_events


def test_bowled(mock_innings: Innings):
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, mock_innings)
    assert mock_innings.current_bowler_innings.wickets == 1
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    assert mock_innings.on_strike_innings.balls_faced == 1


def test_caught(mock_innings: Innings):
    catcher = 12
    payloads = [
        {
            "score_text": "W",
            "dismissal": {
                "type": "ct",
                "fielder": catcher,
            },
        }
    ]
    apply_ball_events(payloads, mock_innings)
    assert mock_innings.current_bowler_innings.wickets == 1
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    prev_ball = mock_innings.previous_ball
    assert catcher == prev_ball.dismissal.fielder.unique_id


def test_caught_fielder_not_valid(mock_innings: Innings):
    catcher = mock_innings.striker.name
    payloads = [
        {
            "score_text": "W",
            "dismissal": {
                "type": "ct",
                "fielder": catcher,
            },
        }
    ]
    with pytest.raises(EngineError) as exc:
        apply_ball_events(payloads, mock_innings)


def test_run_out(mock_innings: Innings):
    thrower = 12
    on_strike_player = mock_innings.striker
    payloads = [
        {
            "score_text": "2W",
            "dismissal": {
                "type": "ro",
                "fielder": thrower,
                "batter": on_strike_player.name,
            },
        }
    ]
    apply_ball_events(payloads, mock_innings)
    assert mock_innings.current_bowler_innings.wickets == 0
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    assert (
        mock_innings.off_strike_innings.batting_state == BatterInningsState.IN_PROGRESS
    )
    assert mock_innings.on_strike_innings.runs_scored == 2
    prev_ball = mock_innings.previous_ball
    assert thrower == prev_ball.dismissal.fielder.unique_id


def test_run_out_missing_batter(mock_innings: Innings):
    thrower = 12
    payloads = [
        {
            "score_text": "2W",
            "dismissal": {
                "type": "ro",
                "fielder": thrower,
            },
        }
    ]
    with pytest.raises(EngineError):
        apply_ball_events(payloads, mock_innings)
    assert "dismissal type run out must specify batter"


def test_innings_completed_event(mock_innings: Innings):
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    on_strike_player = mock_innings.striker
    apply_ball_events(payloads, mock_innings)
    payload = {"batter": on_strike_player.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(payload)
    assert mock_innings.on_strike_innings is None


def test_innings_completed_event_off_strike(mock_innings: Innings):
    thrower = 12
    off_strike_player = mock_innings.non_striker
    payloads = [
        {
            "score_text": "1W",
            "dismissal": {
                "type": "ro",
                "fielder": thrower,
                "batter": off_strike_player.name,
            },
        }
    ]
    apply_ball_events(payloads, mock_innings)
    payload = {"batter": off_strike_player.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(payload)
    assert mock_innings.off_strike_innings.runs_scored == 1
    assert mock_innings.on_strike_innings is None


def test_new_batter_innings(mock_innings: Innings):
    prev_on_strike_player = mock_innings.striker
    off_strike_player = mock_innings.non_striker
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, mock_innings)
    bic_payload = {"batter": prev_on_strike_player.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(bic_payload)
    bis_payload = {"batter": 2}
    mock_innings.handle_batter_innings_started(bis_payload)
    assert mock_innings.striker.unique_id == 2
    assert mock_innings.non_striker == off_strike_player
    prev_batter_innings = mock_innings.get_batter_innings(prev_on_strike_player)
    assert prev_batter_innings.batting_state == BatterInningsState.DISMISSED


def test_new_batter_innings_explicit(mock_innings: Innings):
    prev_on_strike_player = mock_innings.striker
    off_strike_player = mock_innings.non_striker
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, mock_innings)
    bic_payload = {"batter": prev_on_strike_player.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(bic_payload)
    bis_payload = {"batter": 2}
    mock_innings.handle_batter_innings_started(bis_payload)
    assert mock_innings.striker.unique_id == 2
    assert mock_innings.non_striker == off_strike_player
    prev_batter_innings = mock_innings.get_batter_innings(prev_on_strike_player)
    assert prev_batter_innings.batting_state == BatterInningsState.DISMISSED


def test_new_batter_order_num(mock_innings: Innings):
    prev_on_strike_player = mock_innings.striker
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, mock_innings)
    bic_payload = {"batter": prev_on_strike_player.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(bic_payload)
    bis_payload = {"batter": 2}
    mock_innings.handle_batter_innings_started(bis_payload)
    assert mock_innings.on_strike_innings.order_num == 3
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, mock_innings)
    bic_payload = {"batter": mock_innings.striker.name, "reason": "d"}
    mock_innings.handle_batter_innings_completed(bic_payload)
    bis_payload = {"batter": 3}
    mock_innings.handle_batter_innings_started(bis_payload)
    assert mock_innings.on_strike_innings.order_num == 4
    assert mock_innings.off_strike_innings.order_num == 2
