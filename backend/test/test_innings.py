import pytest

from scorpyo.definitions.match import MatchType
from scorpyo.error import EngineError
from scorpyo.event import InningsCompletedEvent
from scorpyo.innings import Innings, InningsState, BatterInningsState
from scorpyo.over import OverState
from scorpyo.registrar import EntityRegistrar
from .conftest import MockMatch
from .resources import HOME_PLAYERS
from .common import apply_ball_events


def test_ball_completed(mock_innings: Innings, registrar: EntityRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    mock_innings.handle_ball_completed(payload)
    event = mock_innings.command_registrar.peek()
    assert event.ball_score.runs_off_bat == 1
    assert mock_innings.off_strike_innings.runs_scored == 1
    assert mock_innings.on_strike_innings.runs_scored == 0


def test_strike_rotates(mock_innings: Innings, registrar: EntityRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    mock_innings.handle_ball_completed(payload)
    event = mock_innings.command_registrar.peek()
    assert event.players_crossed
    assert event.ball_score.runs_off_bat == 1
    expected_on_strike = HOME_PLAYERS[1]
    assert mock_innings.striker == expected_on_strike
    assert mock_innings.off_strike_innings.runs_scored == 1
    assert mock_innings.on_strike_innings.runs_scored == 0
    payload = {"score_text": "1"}
    mock_innings.handle_ball_completed(payload)
    expected_on_strike = HOME_PLAYERS[0]
    assert mock_innings.striker == expected_on_strike
    payload = {"score_text": "2"}
    mock_innings.handle_ball_completed(payload)
    assert mock_innings.striker == expected_on_strike


def test_multiple_deliveries(mock_innings: Innings, registrar: EntityRegistrar):
    payloads = [{"score_text": "1"}, {"score_text": "2"}, {"score_text": "."}]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.off_strike_innings.runs_scored == 1
    assert mock_innings.on_strike_innings.runs_scored == 2
    assert mock_innings.bowler_innings._score.runs_against_bowler == 3


def test_balls_faced_bowled(mock_innings: Innings, registrar: EntityRegistrar):
    payloads = [
        {"score_text": "1"},
        {"score_text": "2"},
        {"score_text": "1lb"},
        {"score_text": "2lb"},
        {"score_text": "2w"},
    ]
    apply_ball_events(payloads, registrar, mock_innings)
    assert mock_innings.on_strike_innings.balls_faced == 2
    assert mock_innings.off_strike_innings.balls_faced == 2
    assert mock_innings.bowler_innings.balls_bowled == 4


def test_innings_completed_all_out(
    mock_match: MockMatch, mock_innings: Innings, registrar: EntityRegistrar
):
    new_batter = mock_match.apply_wickets(8)
    batters_at_crease = [mock_innings.non_striker.name, new_batter]
    expected_ytb = [mock_innings.batting_lineup[-1]]
    actual_atc = [i.player.name for i in mock_innings.active_batter_inningses]
    assert set(mock_innings.yet_to_bat) == set(expected_ytb)
    assert set(batters_at_crease) == set(actual_atc)
    payload = {"reason": InningsState.ALL_OUT}
    with pytest.raises(EngineError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match(r"there are still batters remaining")
    next_to_dismiss = new_batter
    new_batter = mock_innings.batting_lineup[-1]
    mock_match.swap_batters(next_to_dismiss, new_batter)
    with pytest.raises(EngineError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match(r"there are still two batters at the crease")
    # apply the final wicket manually
    mock_match.end_batter_innings(mock_innings.on_strike_innings)
    mock_match.handle_innings_completed(payload)
    assert mock_innings.state == InningsState.ALL_OUT


def test_innings_completed_overs_complete(mock_match: MockMatch, mock_innings: Innings):
    next_bowler = mock_match.apply_overs(mock_match.max_overs() - 1)
    payload = {
        "over_num": 21,
        "reason": InningsState.OVERS_COMPLETE,
    }
    with pytest.raises(EngineError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match("the allotted number of overs has not been bowled")
    mock_match.apply_over(next_bowler)
    mock_match.handle_innings_completed(payload)
    assert mock_innings.state == InningsState.OVERS_COMPLETE


def test_innings_completed_not_in_progress(
    mock_match: MockMatch, mock_innings: Innings
):
    payload = {"reason": InningsState.OVERS_COMPLETE}
    mock_innings.state = InningsState.OVERS_COMPLETE
    with pytest.raises(EngineError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match("innings 0 is not in progress")


def test_innings_completed_target_reached(mock_match: MockMatch, mock_innings: Innings):
    mock_innings.target = 100
    innings_complete_payload = {
        "reason": InningsState.TARGET_REACHED,
    }
    with pytest.raises(EngineError) as exc:
        mock_match.handle_innings_completed(innings_complete_payload)
    assert exc.match("target has not been reached.*target=100 current_score=0")
    mock_innings._score.runs_off_bat = 101
    mock_match.handle_innings_completed(innings_complete_payload)
    assert mock_innings.state == InningsState.TARGET_REACHED


def test_innings_completed_cleanup(
    mock_innings: Innings, mock_match: MockMatch, registrar: EntityRegistrar
):
    mock_match.apply_wickets(9)
    payloads = [
        {"score_text": "1"},
        {"score_text": "1"},
        {"score_text": "1"},
        {"score_text": "1"},
        {"score_text": "1"},
    ]
    apply_ball_events(payloads, registrar, mock_innings)
    off_strike_innings = mock_innings.off_strike_innings
    mock_match.end_batter_innings(mock_innings.on_strike_innings)
    innings_complete_payload = {
        "reason": InningsState.ALL_OUT,
    }
    mock_match.handle_innings_completed(innings_complete_payload)
    assert mock_innings.current_over.state == OverState.INNINGS_ENDED
    assert off_strike_innings.batting_state == BatterInningsState.INNINGS_COMPLETE


def test_innings_numbers(mock_match: MockMatch, mock_innings: Innings, monkeypatch):
    mock_match.max_overs = lambda: 1
    mock_match.match_type = MatchType("dummy", "dmy", 2, 20, 1, 10)
    second_innings_payload = {
        "batting_team": mock_innings.bowling_team.name,
        "opening_bowler": mock_innings.batting_lineup[10].name,
    }
    ice = InningsCompletedEvent(0, None, InningsState.OVERS_COMPLETE)
    mock_match.on_innings_completed(ice)
    mock_match.handle_innings_started(second_innings_payload)
    second_innings = mock_match.current_innings
    assert second_innings.match_innings_num == 1
    assert second_innings.batting_team_innings_num == 0
    ice = InningsCompletedEvent(1, None, InningsState.OVERS_COMPLETE)
    mock_match.on_innings_completed(ice)
    third_innings_payload = {
        "batting_team": second_innings.bowling_team.name,
        "opening_bowler": second_innings.batting_lineup[10].name,
    }
    mock_match.handle_innings_started(third_innings_payload)
    third_innings = mock_match.current_innings
    # pflanagan: we index all innings from 0, so 2 is actually 3
    assert third_innings.match_innings_num == 2
    assert third_innings.batting_team_innings_num == 1
