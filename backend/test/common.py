import os

from scorpyo.entity import Team
from scorpyo.innings import Innings
from scorpyo.match import Match
from scorpyo.registrar import EntityRegistrar

RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "resources")
TEST_CONFIG_PATH = os.path.join(RESOURCES_PATH, "test_config.cfg")
TEST_ENTITIES_DIR = os.path.join(RESOURCES_PATH, "entities")
TEST_ENTITIES_CONFIG = {"loader": "file", "source": TEST_ENTITIES_DIR}


def apply_ball_events(
    payloads: list[dict], registrar: EntityRegistrar, mock_innings: Innings
):
    for payload in payloads:
        mock_innings.handle_ball_completed(payload)


def start_innings(match: Match, batting_team: str):
    payload = {"batting_team": batting_team}
    match.handle_innings_started(payload)
    innings = match.current_innings
    batting_lineup = innings.batting_lineup
    bowling_lineup = innings.bowling_lineup
    innings.handle_batter_innings_started({"batter": batting_lineup[0].name})
    innings.handle_batter_innings_started({"batter": batting_lineup[1].name})
    innings.handle_over_started({"bowler": bowling_lineup[-1].name})
