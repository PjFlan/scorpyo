import pytest

from static_data import score


def scores_equal(score_one, score_two):
    if score_one.runs_off_bat != score_two.runs_off_bat:
        return False
    if score_one.wide_runs != score_two.wide_runs:
        return False
    if score_one.wide_deliveries != score_two.wide_deliveries:
        return False
    if score_one.valid_deliveries != score_two.valid_deliveries:
        return False
    if score_one.leg_byes != score_two.leg_byes:
        return False
    if score_one.byes != score_two.byes:
        return False
    if score_one.no_ball_runs != score_two.no_ball_runs:
        return False
    if score_one.penalty_runs != score_two.penalty_runs:
        return False
    if score_one.wickets != score_two.wickets:
        return False
    return True


@pytest.mark.parametrize(
    "test_input,expected",
    [
        (".", score.DOT_BALL),
        ("w", score.WIDE_BALL),
        ("W", score.WICKET_BALL),
        ("1", score.Score.from_tuple(1, 0, 0, 0, 0, 0, 0)),
        ("4lb", score.Score.from_tuple(0, 0, 4, 0, 0, 0, 0)),
    ],
)
def test_score_parser(test_input, expected):
    assert scores_equal(score.Score.parse(test_input), expected)


def test_add_score():
    score_one = score.Score.from_tuple(4, 0, 0, 0, 0, 0, 0)
    score_two = score.Score.from_tuple(0, 2, 0, 0, 0, 0, 0)
    score_three = score.Score.from_tuple(0, 0, 2, 0, 0, 0, 0)
    score_four = score.Score.from_tuple(0, 0, 0, 0, 1, 0, 0)
    score_accumulated = score_one.add(score_two)
    score_accumulated.add(score_three)
    score_accumulated.add(score_four)
    assert score_accumulated.get_total_runs() == 9
    assert score_accumulated.get_ran_runs() == 6
    assert score_accumulated.get_extra_runs() == 5


def test_get_runs_scored():
    score_text = "."
    test_score = score.Score.parse(score_text)
    assert test_score.runs_off_bat == 0
