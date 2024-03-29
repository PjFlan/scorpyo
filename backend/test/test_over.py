from typing import List

import pytest

from scorpyo.error import EngineError
from scorpyo.innings import Innings
from scorpyo.over import OverState
from scorpyo.registrar import EntityRegistrar
from scorpyo.definitions.match import MatchType
from test.common import apply_ball_events


def rotate_bowlers(mock_innings: Innings, bowlers: List[str], total_overs: int) -> int:
    payloads = [{"score_text": "."}] * 6
    apply_ball_events(payloads, mock_innings)
    oc_payload = {
        "bowler": bowlers[0],
        "reason": OverState.COMPLETED.value,
    }
    mock_innings.handle_over_completed(oc_payload)
    idx = 0
    for i in range(1, total_overs):
        idx = i % len(bowlers)
        os_payload = {"bowler": bowlers[idx]}
        mock_innings.handle_over_started(os_payload)
        apply_ball_events(payloads, mock_innings)
        oc_payload = {
            "bowler": bowlers[idx],
            "reason": OverState.COMPLETED.value,
        }
        mock_innings.handle_over_completed(oc_payload)
    return idx


def test_over_completed(mock_innings: Innings):
    orig_on_strike = mock_innings.striker
    orig_off_strike = mock_innings.non_striker
    payloads = [{"score_text": "1"}] * 6
    apply_ball_events(payloads, mock_innings)
    assert mock_innings.striker == orig_on_strike
    oc_payload = {
        "bowler": mock_innings.current_bowler.name,
        "reason": OverState.COMPLETED.value,
    }
    mock_innings.handle_over_completed(oc_payload)
    assert mock_innings.striker == orig_off_strike
    assert mock_innings.off_strike_innings.runs_scored == 3
    assert mock_innings.runs_scored == 6
    assert mock_innings.current_over.state == OverState.COMPLETED
    bowler_innings = mock_innings.current_bowler_innings
    assert bowler_innings.overs_completed == 1
    assert bowler_innings.balls_bowled == 6
    assert bowler_innings.current_over.balls_bowled == 6


# TODO: this is probably too coupled to the dismissal logic
# should make a helper class that applies a wicket
def test_over_completed_wicket(mock_innings: Innings):
    payloads = [{"score_text": "1"}] * 5
    thrower = 12
    batter_out = 0
    wicket_payload = {
        "score_text": "1W",
        "dismissal": {
            "type": "ro",
            "fielder": thrower,
            "batter": batter_out,
        },
    }
    payloads.append(wicket_payload)
    apply_ball_events(payloads, mock_innings)
    bic_payload = {"batter": batter_out, "reason": "d"}
    mock_innings.handle_batter_innings_completed(bic_payload)
    assert mock_innings.non_striker == "Jack Tector"
    assert mock_innings.striker is None
    bis_payload = {"batter": "Harry Tector"}
    mock_innings.handle_batter_innings_started(bis_payload)
    assert mock_innings.striker == "Harry Tector"
    oc_payload = {
        "bowler": mock_innings.current_bowler.name,
        "reason": OverState.COMPLETED.value,
    }
    mock_innings.handle_over_completed(oc_payload)
    assert mock_innings.striker == "Jack Tector"


def test_incorrect_get_balls_bowled(mock_innings: Innings):
    payloads = [{"score_text": "1"}] * 5
    apply_ball_events(payloads, mock_innings)
    with pytest.raises(EngineError):
        oc_payload = {
            "bowler": mock_innings.current_bowler.name,
            "reason": OverState.COMPLETED.value,
        }
        mock_innings.handle_over_completed(oc_payload)


def test_incorrect_legal_balls(mock_innings: Innings):
    payloads = [{"score_text": "1"}] * 5
    payloads.append({"score_text": "1w"})
    apply_ball_events(payloads, mock_innings)
    with pytest.raises(EngineError):
        oc_payload = {
            "bowler": mock_innings.current_bowler.name,
            "reason": OverState.COMPLETED.value,
        }
        mock_innings.handle_over_completed(oc_payload)


def test_over_started(mock_innings: Innings):
    payloads = [{"score_text": "1"}] * 6
    apply_ball_events(payloads, mock_innings)
    prev_bowler = mock_innings.current_bowler
    new_bowler = "JJ Cassidy"
    assert new_bowler != mock_innings.current_bowler
    oc_payload = {
        "bowler": mock_innings.current_bowler.name,
        "reason": OverState.COMPLETED.value,
    }
    mock_innings.handle_over_completed(oc_payload)
    os_payload = {"bowler": new_bowler}
    mock_innings.handle_over_started(os_payload)
    assert mock_innings.current_bowler == new_bowler
    assert mock_innings.current_bowler_innings.balls_bowled == 0
    prev_over_innings = mock_innings.get_bowler_innings(prev_bowler)
    assert prev_over_innings.player == prev_bowler
    payloads = [{"score_text": "1"}]
    apply_ball_events(payloads, mock_innings)
    curr_over_innings = mock_innings.current_bowler_innings
    assert curr_over_innings.balls_bowled == 1
    assert curr_over_innings.total_runs == 1
    assert prev_over_innings.balls_bowled == 6
    assert curr_over_innings.current_over.balls_bowled == 1


def test_over_started_same_bowler(mock_innings: Innings):
    payloads = [{"score_text": "1"}] * 6
    apply_ball_events(payloads, mock_innings)
    new_bowler = mock_innings.current_bowler
    assert new_bowler == mock_innings.current_bowler
    oc_payload = {
        "bowler": mock_innings.current_bowler.name,
        "reason": OverState.COMPLETED.value,
    }
    mock_innings.handle_over_completed(oc_payload)
    os_payload = {"bowler": new_bowler.name}
    with pytest.raises(EngineError):
        mock_innings.handle_over_started(os_payload)


def test_over_started_exceeds_limit(mock_innings: Innings):
    # patch this with a larger bowler limit as will test this logic separately
    mock_innings.match.match_type = MatchType("dummy", 1, 20, 1, 10, "dummy")
    max_overs = mock_innings.match.max_overs()
    bowlers = [mock_innings.current_bowler.name, "JJ Cassidy"]
    last_bowler_idx = rotate_bowlers(mock_innings, bowlers, max_overs)
    assert len(mock_innings.overs) == max_overs
    with pytest.raises(EngineError) as exc:
        next_bowler_idx = (last_bowler_idx + 1) % len(bowlers)
        os_payload = {"bowler": bowlers[next_bowler_idx]}
        mock_innings.handle_over_started(os_payload)
        assert exc.value == f"innings already has max number of overs {max_overs}"


def test_over_started_bowler_exceeds_limit(mock_innings: Innings):
    total_overs = 8
    bowlers = [mock_innings.current_bowler.name, "JJ Cassidy"]
    last_bowler_idx = rotate_bowlers(mock_innings, bowlers, total_overs)
    with pytest.raises(EngineError) as exc:
        next_bowler_idx = (last_bowler_idx + 1) % len(bowlers)
        os_payload = {"bowler": bowlers[next_bowler_idx]}
        mock_innings.handle_over_started(os_payload)
        assert exc.match(r"has already bowled their full allotment of overs")
