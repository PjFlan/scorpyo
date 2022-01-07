from scorpyo.innings import Innings
from scorpyo.registrar import EntityRegistrar


def apply_ball_events(
    payloads: list[dict], registrar: EntityRegistrar, mock_innings: Innings
):
    for payload in payloads:
        mock_innings.handle_ball_completed(payload)
