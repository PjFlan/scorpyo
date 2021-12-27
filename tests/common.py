from events import BallCompletedEvent
from innings import Innings
from registrar import FixedDataRegistrar


def apply_ball_events(
    payloads: list[dict], registrar: FixedDataRegistrar, mock_innings: Innings
):
    for payload in payloads:
        mock_innings.handle_ball_completed(payload)
