import util
from dismissal import Dismissal, BatterInningsState
from events import (
    BallCompletedEvent,
    InningsStartedEvent,
    BatterInningsCompletedEvent,
    BatterInningsStartedEvent,
)
from over import Over
from player import Player
from score import Scoreable


class Innings(Scoreable):
    def __init__(self, ise: InningsStartedEvent):
        super().__init__()
        self.start_time = ise.start_time
        self.innings_id = ise.innings_id
        self.batting_team = ise.batting_team
        self.bowling_team = ise.bowling_team
        batter_one = ise.batting_team.batter_by_position(0)
        batter_two = ise.batting_team.batter_by_position(1)
        first_over = Over(
            self.innings_id,
            0,
            batter_one,
            batter_two,
            ise.opening_bowler,
        )
        self.bowler_innings = BowlerInnings(ise.opening_bowler, first_over)
        self.overs = [first_over]
        self.on_strike_innings = batter_innings_one = BatterInnings(batter_one)
        self.off_strike_innings = batter_innings_two = BatterInnings(batter_two)
        self.bowler_inningses = [BowlerInnings(ise.opening_bowler, first_over)]
        self.batter_inningses = [batter_innings_one, batter_innings_two]
        self.ball_in_innings_num = 0
        self.ball_in_over_num = 0

    def get_current_over(self):
        return self.overs[-1]

    def get_striker(self):
        if not self.on_strike_innings:
            return None
        return self.on_strike_innings.player

    def get_non_striker(self):
        if not self.off_strike_innings:
            return None
        return self.off_strike_innings.player

    def get_current_bowler(self) -> Player:
        return self.get_current_over().bowler

    def get_wickets_down(self) -> int:
        return self._score.get_wickets()

    def get_next_batter(self) -> Player:
        num_down = self.get_wickets_down()
        next_batter_index = num_down + 1
        try:
            next_batter = self.batting_team.batter_by_position(next_batter_index)
        except IndexError as e:
            raise e
        return next_batter

    def get_batter_innings(self, player: Player) -> "BatterInnings":
        batter_innings = find_innings(player, self.batter_inningses)
        return batter_innings

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)
        ball_increment = 1 if bce.ball_score.is_valid_delivery() else 0
        self.ball_in_innings_num += ball_increment
        self.ball_in_over_num += ball_increment
        self.on_strike_innings.on_ball_completed(bce)
        if bce.dismissal:
            dismissed_innings = find_innings(
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

    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent):
        if bic.batter not in self.batting_team:
            raise ValueError(
                "batter {bic.batter} is not part of batting team {" "self.batting_team}"
            )
        dismissed_innings = find_innings(bic.batter, self.batter_inningses)
        if bic.batting_state == BatterInningsState.DISMISSED:
            prev_dismissal = self.get_previous_ball().dismissal
            if not prev_dismissal:
                raise ValueError(
                    "inconsistent state: batter innings completed via "
                    "dismissal but previous delivery has no associated "
                    "dismissal"
                )
            elif prev_dismissal.batter != bic.batter:
                raise ValueError(
                    f"batter dismissed in previous ball: "
                    f"{prev_dismissal.batter} does not equal batter "
                    f"whose innings has just completed: {bic.batter}"
                )
            if dismissed_innings.batting_state != BatterInningsState.DISMISSED:
                raise ValueError(
                    "inconsistent state: batter innings completed via a"
                    "dismissal but batter is currently in state: "
                    "{dismissed_innings.batting_state}"
                )
        if dismissed_innings == self.on_strike_innings:
            self.on_strike_innings = None
        else:
            self.off_strike_innings = None

    def on_batter_innings_started(self, bis: BatterInningsStartedEvent):
        if self.on_strike_innings and self.off_strike_innings:
            raise ValueError(
                "there are already two batters at the crease. Must "
                "complete one of their innings before beginning a new one"
            )
        try:
            existing = find_innings(bis.batter, self.batter_inningses)
        except ValueError:
            existing = None
        if (
            existing
            and not existing.batting_state != BatterInningsState.RETIRED_NOT_OUT
        ):
            raise ValueError(
                "batter {existing.batter} has already batted and cannot "
                "bat again (current state {existing.batting_state})"
            )
        new_innings = BatterInnings(bis.batter)
        self.batter_inningses.append(new_innings)
        if not self.on_strike_innings:
            self.on_strike_innings = new_innings
        else:
            self.off_strike_innings = new_innings


class BatterInnings(Scoreable):
    def __init__(self, player: Player):
        super().__init__()
        self.player = player
        self.balls = []
        self.dismissal = None
        self.batting_state = BatterInningsState.IN_PROGRESS

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)

    def balls_faced(self):
        return self._score.valid_deliveries

    def on_dismissal(self, dismissal: Dismissal):
        self.dismissal = dismissal
        self.batting_state = BatterInningsState.DISMISSED


class BowlerInnings(Scoreable):
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
        super().update_score(bce)
        if bce.dismissal and bce.dismissal.bowler_accredited():
            self.wickets += 1


def find_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError(f"no innings found for player: {player}")
