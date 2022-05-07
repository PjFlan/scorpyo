import pytest

from scorpyo.engine import MatchEngine
from scorpyo.error import EngineError, RejectReason
from scorpyo.match import MatchState
from test.resources import HOME_TEAM, AWAY_TEAM


class MockEngineListener:

    messages = []

    def on_message(self, message: dict):
        self.messages.append(message)


@pytest.fixture()
def engine_listener():
    mock_listener = MockEngineListener()
    return mock_listener


def test_match_started(registrar):
    engine = MatchEngine(registrar)
    command = {"match_type": "OD", "home_team": HOME_TEAM, "away_team": AWAY_TEAM}
    engine.handle_match_started(command)
    assert engine.current_match.state == MatchState.IN_PROGRESS
    assert engine.current_match.home_team == HOME_TEAM
    assert engine.current_match.away_team == AWAY_TEAM


def test_reject_no_event(registrar, engine_listener):
    engine = MatchEngine(registrar)
    engine.register_client(engine_listener)
    command_id = 0
    command = {
        "command_id": command_id,
        "match_type": "bad_type",
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
    }
    engine.on_event(command)
    message = engine_listener.messages[-1]
    assert message["reject_reason"] == RejectReason.BAD_COMMAND.value
    assert message["message_id"] == command_id
