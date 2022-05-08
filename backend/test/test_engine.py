from scorpyo.error import RejectReason
from scorpyo.event import EventType
from scorpyo.match import MatchState
from test.resources import HOME_TEAM, AWAY_TEAM


def test_match_started(registrar, mock_engine):
    command = {"match_type": "OD", "home_team": HOME_TEAM, "away_team": AWAY_TEAM}
    mock_engine.handle_match_started(command)
    assert mock_engine.current_match.state == MatchState.IN_PROGRESS
    assert mock_engine.current_match.home_team == HOME_TEAM
    assert mock_engine.current_match.away_team == AWAY_TEAM


def test_reject_no_event(registrar, mock_engine):
    command_id = 0
    command = {
        "command_id": command_id,
        "match_type": "OD",
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
    }
    mock_engine.on_command(command)
    message = mock_engine._messages[-1]
    assert message["reject_reason"] == RejectReason.BAD_COMMAND.value
    assert message["message_id"] == command_id


def test_reject_no_command(registrar, mock_engine):
    command = {
        "event": EventType.MATCH_STARTED.value,
        "match_type": "OD",
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
    }
    mock_engine.on_command(command)
    message = mock_engine._messages[-1]
    assert message["reject_reason"] == RejectReason.BAD_COMMAND.value
