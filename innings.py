from over import Over
from player import Player
import util


class Innings(util.Scoreable):

    def __init__(self, innings_started_event):
        super().__init__()
        self.start_time = innings_started_event.start_time
        self.innings_id = innings_started_event.innings_id
        self.batting_team = innings_started_event.batting_team
        self.bowling_team = innings_started_event.bowling_team
        opening_bowler = innings_started_event.opening_bowler
        batter_one = innings_started_event.batting_team.batter_by_position(0)
        batter_two = innings_started_event.batting_team.batter_by_position(1)
        first_over = Over(self.innings_id, 0, batter_one, batter_two, opening_bowler)
        self.overs = [first_over]
        opening_bowler_innings = BowlingInnings(opening_bowler, first_over)
        batter_innings_one = self.on_strike_innings = BattingInnings(batter_one)
        batter_innings_two = self.off_strike_innings = BattingInnings(batter_two)
        self.bowler_inningses = [opening_bowler_innings]
        self.batter_inningses = [batter_innings_one, batter_innings_two]

    def get_current_over(self):
        return self.overs[-1]

    def get_striker(self):
        return self.on_strike_innings.player

    def get_non_striker(self):
        return self.off_strike_innings.player

    def get_current_bowler(self):
        return self.get_current_over().bowler

    def on_ball_completed(self, ball_completed_event):
        super().on_ball_completed(ball_completed_event)
        self.on_strike_innings.on_ball_completed(ball_completed_event)
        self.off_strike_innings.on_ball_completed(ball_completed_event)
        bowler_innings = find_innings(self.get_current_bowler(), self.bowler_inningses)
        bowler_innings.on_ball_completed(ball_completed_event)
        self.get_current_over().on_ball_completed(ball_completed_event)
        if ball_completed_event.players_crossed:
            self.on_strike_innings, self.off_strike_innings = util.switch_strike(
                                                                self.on_strike_innings,
                                                                self.off_strike_innings)


class BattingInnings(util.Scoreable):

    def __init__(self, player: Player):
        super().__init__()
        self.player = player
        self.balls = []
        self.dismissal = None

    def on_ball_completed(self, ball_completed_event):
        if ball_completed_event.on_strike == self.player:
            super().on_ball_completed(ball_completed_event)


class BowlingInnings(util.Scoreable):

    def __init__(self, player: Player, first_over: Over):
        super().__init__()
        self.player = player
        self.overs = [first_over]
        self.balls = []

    def on_ball_completed(self, ball_completed_event):
        super().on_ball_completed(ball_completed_event)


def find_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError(f"no innings found for player: {player}")
