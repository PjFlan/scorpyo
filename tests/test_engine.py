from scorpyo.engine import MatchEngine
from scorpyo.match import MatchState
from tests.resources import HOME_TEAM, AWAY_TEAM


def test_match_started(registrar):
    engine = MatchEngine()
    message = {"match_type": "ODI", "home_team": HOME_TEAM, "away_team": AWAY_TEAM}
    engine.handle_match_started(message)
    assert engine.current_match.state == MatchState.IN_PROGRESS
    assert engine.current_match.home_team == HOME_TEAM
    assert engine.current_match.away_team == AWAY_TEAM
    # clean up static data
    MatchEngine.match_id = 0
