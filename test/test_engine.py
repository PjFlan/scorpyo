from scorpyo.engine import MatchEngine
from scorpyo.match import MatchState
from test.resources import HOME_TEAM, AWAY_TEAM


def test_match_started(registrar):
    engine = MatchEngine(registrar)
    message = {"match_type": "OD", "home_team": HOME_TEAM, "away_team": AWAY_TEAM}
    engine.handle_match_started(message)
    assert engine.current_match.state == MatchState.IN_PROGRESS
    assert engine.current_match.home_team == HOME_TEAM
    assert engine.current_match.away_team == AWAY_TEAM
    # clean up static data
    MatchEngine.match_id = 0
