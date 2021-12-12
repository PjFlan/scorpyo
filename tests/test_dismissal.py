from innings import Innings, BatterInningsState
from registrar import FixedDataRegistrar
from common import apply_ball_events


def test_dismissal(mock_innings: Innings, registrar: FixedDataRegistrar):
    payloads = [{"score_text": "W", "dismissal": {"type": "b"}}]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.bowler_innings.wickets == 1
    assert mock_innings.on_strike_innings.batting_state == BatterInningsState.DISMISSED
    assert mock_innings.on_strike_innings.balls_faced() == 1
