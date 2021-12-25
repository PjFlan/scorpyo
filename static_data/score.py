from score import Score


BLANK_SCORE = Score(0, 0, 0, 0, 0, 0, 0)
DOT_BALL = Score.from_tuple(0, 0, 0, 0, 0, 0, 0)
WICKET_BALL = Score.from_tuple(0, 0, 0, 0, 0, 0, 1)
WIDE_BALL = Score.from_tuple(0, 1, 0, 0, 0, 0, 0)
