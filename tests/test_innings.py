from events import BallCompletedEvent
from static_data import HOME_PLAYERS


def test_ball_completed(mux, registrar, mock_innings):
    payload = {"score_text": "1"}
    assert mock_innings.get_striker() == HOME_PLAYERS[0]
    event = BallCompletedEvent.build(payload, mock_innings)
    assert event.players_crossed
    assert event.ball_score.runs_off_bat == 1
    mock_innings.on_ball_completed(event)
    assert mock_innings.get_striker() == HOME_PLAYERS[1]
    assert mock_innings.off_strike_innings.runs_scored() == 1
    assert mock_innings.on_strike_innings.runs_scored() == 0
