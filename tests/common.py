import os

from scorpyo.innings import Innings
from scorpyo.registrar import EntityRegistrar


RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "resources")
TEST_CONFIG_PATH = os.path.join(RESOURCES_PATH, "test_config.cfg")
TEST_ENTITIES_DIR = os.path.join(RESOURCES_PATH, "entities")
TEST_CONFIG = {"loader": "file", "source": TEST_ENTITIES_DIR}


def apply_ball_events(
    payloads: list[dict], registrar: EntityRegistrar, mock_innings: Innings
):
    for payload in payloads:
        mock_innings.handle_ball_completed(payload)
