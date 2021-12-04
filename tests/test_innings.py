from events import BallCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar
from static_data import HOME_PLAYERS


def test_ball_completed(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.get_striker() == HOME_PLAYERS[0]
    event = BallCompletedEvent.build(payload,
                                     mock_innings.get_striker(),
                                     mock_innings.get_non_striker(),
                                     mock_innings.get_current_bowler(),
                                     registrar)
    assert event.ball_score.runs_off_bat == 1
    mock_innings.on_ball_completed(event)
    assert mock_innings.off_strike_innings.runs_scored() == 1
    assert mock_innings.on_strike_innings.runs_scored() == 0


def test_strike_rotates(mock_innings: Innings, registrar: FixedDataRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.get_striker() == HOME_PLAYERS[0]
    event = BallCompletedEvent.build(payload,
                                     mock_innings.get_striker(),
                                     mock_innings.get_non_striker(),
                                     mock_innings.get_current_bowler(),
                                     registrar)
    assert event.players_crossed
    assert event.ball_score.runs_off_bat == 1
    mock_innings.on_ball_completed(event)
    expected_on_strike = HOME_PLAYERS[1]
    assert mock_innings.get_striker() == expected_on_strike
    assert mock_innings.off_strike_innings.runs_scored() == 1
    assert mock_innings.on_strike_innings.runs_scored() == 0
    payload = {"score_text": "1"}
    event = BallCompletedEvent.build(payload,
                                     mock_innings.get_striker(),
                                     mock_innings.get_non_striker(),
                                     mock_innings.get_current_bowler(),
                                     registrar)
    mock_innings.on_ball_completed(event)
    expected_on_strike = HOME_PLAYERS[0]
    assert mock_innings.get_striker() == expected_on_strike
    payload = {"score_text": "2"}
    event = BallCompletedEvent.build(payload,
                                     mock_innings.get_striker(),
                                     mock_innings.get_non_striker(),
                                     mock_innings.get_current_bowler(),
                                     registrar)
    mock_innings.on_ball_completed(event)
    assert mock_innings.get_striker() == expected_on_strike


def test_multiple_deliveries(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [{"score_text": "1"}, {"score_text": "2"}, {"score_text": "."}]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.off_strike_innings.runs_scored() == 1
    assert mock_innings.on_strike_innings.runs_scored() == 2
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
    assert mock_innings.bowler_innings.balls_bowled() == 4


def apply_ball_events(
    payloads: dict, registrar: FixedDataRegistrar, mock_innings: Innings
):
    for payload in payloads:
        event = BallCompletedEvent.build(payload,
                                         mock_innings.get_striker(),
                                         mock_innings.get_non_striker(),
                                         mock_innings.get_current_bowler(),
                                         registrar)
        mock_innings.on_ball_completed(event)
