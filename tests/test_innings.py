from innings import Innings
from registrar import FixedDataRegistrar
from .static import HOME_PLAYERS
from .common import apply_ball_events


def test_ball_completed(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.get_striker() == HOME_PLAYERS[0]
    event = mock_innings.handle_ball_completed(payload)
    assert event.ball_score.runs_off_bat == 1
    assert mock_innings.off_strike_innings.get_runs_scored() == 1
    assert mock_innings.on_strike_innings.get_runs_scored() == 0


def test_strike_rotates(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.get_striker() == HOME_PLAYERS[0]
    event = mock_innings.handle_ball_completed(payload)
    assert event.players_crossed
    assert event.ball_score.runs_off_bat == 1
    expected_on_strike = HOME_PLAYERS[1]
    assert mock_innings.get_striker() == expected_on_strike
    assert mock_innings.off_strike_innings.get_runs_scored() == 1
    assert mock_innings.on_strike_innings.get_runs_scored() == 0
    payload = {"score_text": "1"}
    mock_innings.handle_ball_completed(payload)
    expected_on_strike = HOME_PLAYERS[0]
    assert mock_innings.get_striker() == expected_on_strike
    payload = {"score_text": "2"}
    mock_innings.handle_ball_completed(payload)
    assert mock_innings.get_striker() == expected_on_strike


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
