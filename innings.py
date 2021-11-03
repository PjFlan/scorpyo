from events import InningsStartedEvent
from over import Over
from player import Player


class Innings:

    def __init__(self, innings_started_event: InningsStartedEvent):
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
        batter_innings_one = self.on_strike = BattingInnings(batter_one)
        batter_innings_two = self.off_strike = BattingInnings(batter_two)
        self.bowler_inningses = [opening_bowler_innings]
        self.batter_inningses = [batter_innings_one, batter_innings_two]

    def get_current_over(self):
        return self.overs[-1]


class BattingInnings:

    def __init__(self, player: Player):
        self.player = player
        self.balls = []
        self.dismissal = None


class BowlingInnings:

    def __init__(self, player: Player, first_over: Over):
        self.player = player
        self.overs = [first_over]
        self.balls = []
