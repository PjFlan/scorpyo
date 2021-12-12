import enum

from dismissal import Dismissal
from events import BallCompletedEvent
from over import Over
from player import Player
import util


class BatterInningsState(enum.Enum):
    IN_PROGRESS = 1
    RETIRED_OUT = 2
    RETIRED_NOT_OUT = 3
    DISMISSED = 4
    STRANDED = 5


class Innings(util.Scoreable):
    def __init__(self, innings_started_event):
        super().__init__()
        self.start_time = innings_started_event.start_time
        self.innings_id = innings_started_event.innings_id
        self.batting_team = innings_started_event.batting_team
        self.bowling_team = innings_started_event.bowling_team
        batter_one = innings_started_event.batting_team.batter_by_position(0)
        batter_two = innings_started_event.batting_team.batter_by_position(1)
        first_over = Over(
            self.innings_id,
            0,
            batter_one,
            batter_two,
            innings_started_event.opening_bowler,
        )
        self.bowler_innings = BowlerInnings(
            innings_started_event.opening_bowler, first_over
        )
        self.overs = [first_over]
        self.on_strike_innings = batter_innings_one = BattingInnings(batter_one)
        self.off_strike_innings = batter_innings_two = BattingInnings(batter_two)
        self.bowler_inningses = [BowlerInnings(self.bowler_innings, first_over)]
        self.batter_inningses = [batter_innings_one, batter_innings_two]
        self.ball_in_innings_num = 0
        self.ball_in_over_num = 0

    def get_current_over(self):
        return self.overs[-1]

    def get_striker(self):
        return self.on_strike_innings.player

    def get_non_striker(self):
        return self.off_strike_innings.player

    def get_current_bowler(self) -> "BowlerInnings":
        return self.get_current_over().bowler

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().on_ball_completed(bce)
        ball_increment = 1 if bce.ball_score.is_valid_delivery() else 0
        self.ball_in_innings_num += ball_increment
        self.ball_in_over_num += ball_increment
        self.on_strike_innings.on_ball_completed(bce)
        if bce.dismissal:
            dismissed_innings = find_player_innings(
                bce.dismissal.batter,
                self.batter_inningses,
            )
            dismissed_innings.on_dismissal(bce.dismissal)
        self.bowler_innings.on_ball_completed(bce)
        self.get_current_over().on_ball_completed(bce)
        if bce.players_crossed:
            self.on_strike_innings, self.off_strike_innings = util.switch_strike(
                self.on_strike_innings, self.off_strike_innings
            )


class BattingInnings(util.Scoreable):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player
        self.balls = []
        self.dismissal = None
        self.batting_state = BatterInningsState.IN_PROGRESS

    def balls_faced(self):
        return self._score.valid_deliveries

    def on_dismissal(self, dismissal: Dismissal):
        self.dismissal = dismissal
        self.batting_state = BatterInningsState.DISMISSED


class BowlerInnings(util.Scoreable):
    def __init__(self, player: Player, first_over: Over):
        super().__init__()
        self.player = player
        self.overs = [first_over]
        self.balls = []
        self.wickets = 0

    def balls_bowled(self):
        return self._score.valid_deliveries

    def runs_against(self):
        return self._score.runs_off_bat + self._score.get_bowler_extras()

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().on_ball_completed(bce)
        if bce.dismissal and bce.dismissal.bowler_accredited():
            self.wickets += 1


def find_player_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError(f"no innings found for player: {player}")
