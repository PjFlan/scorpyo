import enum
from typing import Optional

import util
from context import Context
from dismissal import Dismissal, parse_dismissal
from events import (
    BallCompletedEvent,
    InningsStartedEvent,
    BatterInningsCompletedEvent,
    BatterInningsStartedEvent,
    EventType,
)
from fixed_data import Entities
from over import Over
from player import Player
from score import Scoreable, Score


class Innings(Context, Scoreable):
    def __init__(self, ise: InningsStartedEvent, match: "Match"):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match = match
        self.start_time = ise.start_time
        self.innings_id = ise.innings_id
        self.batting_team = ise.batting_team
        self.bowling_team = ise.bowling_team
        batter_one = ise.batting_team.batter_by_position(0)
        batter_two = ise.batting_team.batter_by_position(1)

        first_over = Over(0, ise.opening_bowler, self)
        self.overs = [first_over]
        self.bowler_innings = BowlerInnings(ise.opening_bowler, first_over, self)
        self.on_strike_innings = batter_innings_one = BatterInnings(batter_one, self)
        self.off_strike_innings = batter_innings_two = BatterInnings(batter_two, self)
        self.bowler_inningses = [self.bowler_innings]
        self.batter_inningses = [batter_innings_one, batter_innings_two]
        self.ball_in_innings_num = 0
        self.ball_in_over_num = 0

        self.add_handler(EventType.BALL_COMPLETED, self.handle_ball_completed)
        self.add_handler(
            EventType.BATTER_INNINGS_STARTED, self.handle_batter_innings_started
        )
        self.add_handler(
            EventType.BATTER_INNINGS_COMPLETED, self.handle_batter_innings_completed
        )

    def get_current_over(self) -> Over:
        return self.overs[-1]

    def get_striker(self) -> Optional[Player]:
        if not self.on_strike_innings:
            return None
        return self.on_strike_innings.player

    def get_non_striker(self) -> Optional[Player]:
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

    def handle_ball_completed(self, payload: dict):
        ball_score = Score.parse(payload["score_text"])
        dismissal_payload = dismissal = None
        on_strike_player = self.get_striker()
        off_strike_player = self.get_non_striker()
        bowler = self.get_current_bowler()
        for key in payload:
            if key == "on_strike":
                on_strike_player = self.fd_registrar.get_fixed_data(
                    Entities.PLAYER, payload[key]
                )
            elif key == "off_strike":
                off_strike_player = self.fd_registrar.get_fixed_data(
                    Entities.PLAYER, payload[key]
                )
            elif key == "bowler":
                bowler = self.fd_registrar.get_fixed_data(Entities.PLAYER, payload[key])
            elif key == "dismissal":
                dismissal_payload = payload[key]
        if dismissal_payload:
            dismissal = parse_dismissal(
                payload["dismissal"],
                on_strike_player,
                off_strike_player,
                bowler,
                self.fd_registrar,
            )
        players_crossed = False
        if ball_score.wide_runs > 0 and ball_score.wide_runs % 2 == 0:
            players_crossed = True
        elif ball_score.get_ran_runs() % 2 == 1:
            players_crossed = True
        bce = BallCompletedEvent(
            on_strike_player,
            off_strike_player,
            bowler,
            ball_score,
            players_crossed,
            dismissal,
        )
        self.on_ball_completed(bce)
        return bce

    def handle_batter_innings_started(self, payload: dict):
        batter = self.fd_registrar.get_fixed_data(Entities.PLAYER, payload["batter"])
        if not batter:
            try:
                batter = self.get_next_batter()
            except IndexError:
                raise ValueError(
                    "cannot process new batter innings as there are no players left"
                )
        bis = BatterInningsStartedEvent(batter)
        self.on_batter_innings_started(bis)
        return bis

    def handle_batter_innings_completed(self, payload: dict):
        batter = self.fd_registrar.get_fixed_data(Entities.PLAYER, payload["batter"])
        state = BatterInningsState(payload["reason"])
        bic = BatterInningsCompletedEvent(batter, state)
        self.on_batter_innings_completed(bic)
        return bic

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
        new_innings = BatterInnings(bis.batter, self)
        self.batter_inningses.append(new_innings)
        if not self.on_strike_innings:
            self.on_strike_innings = new_innings
        else:
            self.off_strike_innings = new_innings

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


class BatterInnings(Scoreable):
    def __init__(self, player: Player, innings: Innings):
        super().__init__()
        self.innings = innings
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
    def __init__(self, player: Player, first_over: Over, innings: Innings):
        super().__init__()
        self.innings = innings
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


class BatterInningsState(enum.Enum):
    IN_PROGRESS = "i"
    RETIRED_OUT = "ro"
    RETIRED_NOT_OUT = "rno"
    DISMISSED = "d"
    STRANDED = "s"


def find_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError(f"no innings found for player: {player}")
