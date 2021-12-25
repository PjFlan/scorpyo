import pytest

from dismissal import BatterInningsState
from events import BatterInningsCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar
from common import apply_ball_events


def test_bowled(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.bowler_innings.wickets == 1
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    assert mock_innings.on_strike_innings.balls_faced() == 1


def test_caught(mock_innings: Innings, registrar: FixedDataRegistrar):
    catcher = "Callum Donnelly"
    payloads = [
        {
            "score_text": "W",
            "dismissal": {
                "type": "ct",
                "fielder": catcher,
            },
        }
    ]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.bowler_innings.wickets == 1
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    prev_ball = mock_innings.get_previous_ball()
    assert prev_ball.dismissal.fielder == catcher


def test_run_out(mock_innings: Innings, registrar: FixedDataRegistrar):
    thrower = "Callum Donnelly"
    on_strike_player = mock_innings.get_striker()
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
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.bowler_innings.wickets == 0
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    assert (
        mock_innings.off_strike_innings.batting_state == BatterInningsState.IN_PROGRESS
    )
    assert mock_innings.on_strike_innings.runs_scored() == 2
    prev_ball = mock_innings.get_previous_ball()
    assert prev_ball.dismissal.fielder == thrower


def test_run_out_missing_batter(mock_innings: Innings, registrar: FixedDataRegistrar):
    thrower = "Callum Donnelly"
    payloads = [
        {
            "score_text": "2W",
            "dismissal": {
                "type": "ro",
                "fielder": thrower,
            },
        }
    ]
    with pytest.raises(ValueError) as exc:
        apply_ball_events(payloads, registrar, mock_innings)
    assert "dismissal type run out must specify batter"


def test_innings_completed_event(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    on_strike_player = mock_innings.get_striker()
    apply_ball_events(payloads, registrar, mock_innings)
    payload = {"batter": on_strike_player.name, "reason": "d"}
    bic = BatterInningsCompletedEvent.build(payload, registrar)
    mock_innings.on_batter_innings_completed(bic)
    assert mock_innings.on_strike_innings is None


def test_innings_completed_event_off_strike(
    mock_innings: Innings, registrar: FixedDataRegistrar
):
    thrower = "Callum Donnelly"
    off_strike_player = mock_innings.get_non_striker()
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
    apply_ball_events(payloads, registrar, mock_innings)
    payload = {"batter": off_strike_player.name, "reason": "d"}
    bic = BatterInningsCompletedEvent.build(payload, registrar)
    mock_innings.on_batter_innings_completed(bic)
    assert mock_innings.off_strike_innings.runs_scored() == 1
    assert mock_innings.on_strike_innings is None