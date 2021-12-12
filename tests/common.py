from events import BallCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar


def apply_ball_events(
    payloads: dict, registrar: FixedDataRegistrar, mock_innings: Innings
):
    for payload in payloads:
        event = BallCompletedEvent.build(
            payload,
            mock_innings.get_striker(),
            mock_innings.get_non_striker(),
            mock_innings.get_current_bowler(),
            registrar,
        )
        mock_innings.on_ball_completed(event)
