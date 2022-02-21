import pytest

from scorpyo.context import Context
from scorpyo.events import InningsCompletedEvent
from scorpyo.innings import Innings, InningsState, BatterInningsState
from scorpyo.registrar import EntityRegistrar
from .conftest import MockMatch
from .resources import HOME_PLAYERS
from .common import apply_ball_events


def test_ball_completed(mock_innings: Innings, registrar: EntityRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    mock_innings.handle_ball_completed(payload)
    event = Context.event_registrar.peek()
    assert event.ball_score.runs_off_bat == 1
    assert mock_innings.off_strike_innings.runs_scored == 1
    assert mock_innings.on_strike_innings.runs_scored == 0


def test_strike_rotates(mock_innings: Innings, registrar: EntityRegistrar):
    payload = {"score_text": "1"}
    assert mock_innings.striker == HOME_PLAYERS[0]
    mock_innings.handle_ball_completed(payload)
    event = Context.event_registrar.peek()
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
    assert mock_innings.bowler_innings.runs_against == 3


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
    # TODO pflanagan: theres a lot of boilerplate here needed to take wickets
    # maybe I should instead patch various methods on my mock class to do this for me
    num_batters = len(mock_innings.batting_lineup)
    batters_at_create = [mock_innings.non_striker.name]
    next_to_dismiss = mock_innings.striker
    for i in range(2, num_batters - 1):
        new_batter = mock_innings.batting_lineup[i]
        mock_match.swap_batters(next_to_dismiss, new_batter)
        next_to_dismiss = new_batter
    batters_at_create.append(new_batter)
    expected_ytb = [mock_innings.batting_lineup[num_batters - 1]]
    actual_atc = [i.player.name for i in mock_innings.active_batter_innings]
    assert set(mock_innings.yet_to_bat) == set(expected_ytb)
    assert set(batters_at_create) == set(actual_atc)
    payload = {"match_innings_num": 0, "reason": InningsState.ALL_OUT}
    with pytest.raises(AssertionError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match(r"there are still batters remaining")
    new_batter = mock_innings.batting_lineup[-1]
    mock_match.swap_batters(next_to_dismiss, new_batter)
    with pytest.raises(AssertionError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match(r"there are still two batters at the crease")
    mock_innings.on_strike_innings.batting_state = BatterInningsState.DISMISSED
    mock_innings.on_strike_innings = None
    mock_match.handle_innings_completed(payload)
    assert mock_innings.state == InningsState.ALL_OUT


def test_innings_completed_overs_complete(mock_match: MockMatch, mock_innings: Innings):
    next_bowler = mock_match.apply_overs(mock_match.max_overs() - 1)
    payload = {
        "over_num": 21,
        "match_innings_num": 0,
        "reason": InningsState.OVERS_COMPLETE,
    }
    with pytest.raises(AssertionError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match("the allotted number of overs has not been bowled")
    mock_match.apply_over(next_bowler)
    mock_match.handle_innings_completed(payload)
    assert mock_innings.state == InningsState.OVERS_COMPLETE


def test_innings_completed_wrong_innings(mock_match: MockMatch, mock_innings: Innings):
    payload = {"match_innings_num": 1, "reason": InningsState.OVERS_COMPLETE}
    with pytest.raises(ValueError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match("the innings number of the InningsCompletedEvent does not match")


def test_innings_completed_not_in_progress(
    mock_match: MockMatch, mock_innings: Innings
):
    payload = {"match_innings_num": 0, "reason": InningsState.OVERS_COMPLETE}
    mock_innings.state = InningsState.OVERS_COMPLETE
    with pytest.raises(ValueError) as exc:
        mock_match.handle_innings_completed(payload)
    assert exc.match("innings 0 is not in progress")


def test_innings_completed_target_reached(mock_match: MockMatch, mock_innings: Innings):
    mock_innings.target = 100
    innings_complete_payload = {
        "match_innings_num": 0,
        "reason": InningsState.TARGET_REACHED,
    }
    with pytest.raises(AssertionError) as exc:
        mock_match.handle_innings_completed(innings_complete_payload)
    assert exc.match("target has not been reached.*target=100 current_score=0")
    mock_innings._score.runs_off_bat = 101
    mock_match.handle_innings_completed(innings_complete_payload)
    assert mock_innings.state == InningsState.TARGET_REACHED


def test_innings_numbers(mock_match: MockMatch, mock_innings: Innings, monkeypatch):
    mock_match.max_overs = lambda: 1
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
