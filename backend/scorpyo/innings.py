from typing import Optional, List

import scorpyo.util as util
from scorpyo.error import EngineError, RejectReason
from scorpyo.util import LOGGER
from scorpyo.context import Context
from scorpyo.dismissal import Dismissal, parse_dismissal
from scorpyo.event import (
    BallCompletedEvent,
    InningsStartedEvent,
    BatterInningsCompletedEvent,
    BatterInningsStartedEvent,
    EventType,
    OverCompletedEvent,
    OverStartedEvent,
    InningsCompletedEvent,
    record_command,
)
from scorpyo.entity import EntityType
from scorpyo.over import Over, OverState
from scorpyo.entity import Player
from scorpyo.score import Scoreable, Score
from scorpyo.definitions.innings import InningsState, BatterInningsState


class Innings(Context, Scoreable):
    def __init__(
        self,
        ise: InningsStartedEvent,
        match: "Match",
        entity_registrar: "EntityRegistrar",
        command_registrar: "CommandRegistrar",
    ):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match = match
        self.entity_registrar = entity_registrar
        self.command_registrar = command_registrar
        self.start_time = ise.start_time
        self.end_time = None
        self.match_innings_num = ise.match_innings_num
        self.batting_team_innings_num = ise.batting_team_innings_num
        self._dismissal_pending = False

        self.target = None
        self.state = InningsState.IN_PROGRESS
        self.batting_lineup = ise.batting_lineup
        self.bowling_lineup = ise.bowling_lineup
        self.batting_team = self.batting_lineup.team
        self.bowling_team = self.bowling_lineup.team
        batter_one = ise.batting_lineup[0]
        batter_two = ise.batting_lineup[1]

        first_over = Over(0, ise.opening_bowler, self)
        self.overs = [first_over]
        self.bowler_innings = BowlerInnings(ise.opening_bowler, first_over, self, 1)
        self.on_strike_innings = batter_innings_one = BatterInnings(batter_one, self, 1)
        self.off_strike_innings = batter_innings_two = BatterInnings(
            batter_two, self, 2
        )
        self.bowler_inningses = [self.bowler_innings]
        self.batter_inningses = [batter_innings_one, batter_innings_two]
        self.ball_in_match_innings_num = 0
        self.ball_in_over_num = 0

        # TODO pflanagan: should be able to link the handlers and the status
        #  dependencies so that the tree is walked automatically based on the handled
        #  events
        self.add_handler(EventType.BALL_COMPLETED, self.handle_ball_completed)
        self.add_handler(
            EventType.BATTER_INNINGS_STARTED, self.handle_batter_innings_started
        )
        self.add_handler(
            EventType.BATTER_INNINGS_COMPLETED, self.handle_batter_innings_completed
        )
        self.add_handler(EventType.OVER_COMPLETED, self.handle_over_completed)
        self.add_handler(EventType.OVER_STARTED, self.handle_over_started)

    @property
    def current_over(self) -> Over:
        return self.overs[-1]

    @property
    def striker(self) -> Optional[Player]:
        if not self.on_strike_innings:
            return None
        return self.on_strike_innings.player

    @property
    def non_striker(self) -> Optional[Player]:
        if not self.off_strike_innings:
            return None
        return self.off_strike_innings.player

    @property
    def current_bowler(self) -> Player:
        return self.current_over.bowler

    @property
    def current_bowler_innings(self) -> Optional["BowlerInnings"]:
        return self.bowler_innings

    @property
    def wickets_down(self) -> int:
        return self._score.wickets

    @property
    def next_batter(self) -> Player:
        num_down = self.wickets_down
        next_batter_index = num_down + 1
        try:
            next_batter = self.batting_lineup[next_batter_index]
        except IndexError:
            msg = "requested next batter but lineup does not contain one"
            LOGGER.error(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        return next_batter

    @property
    def yet_to_bat(self) -> List[Player]:
        players_batted = set(bi.player for bi in self.batter_inningses)
        all_players = set(self.batting_lineup.lineup)
        yet_to_bat = set.difference(all_players, players_batted)
        return list(yet_to_bat)

    @property
    def num_batters_remaining(self) -> int:
        num_batters = len(self.batting_lineup)
        num_already_batted = len(self.batter_inningses)
        assert num_batters >= num_already_batted
        return num_batters - num_already_batted

    @property
    def active_batter_inningses(self) -> List["BatterInnings"]:
        inningses = [
            i
            for i in (self.on_strike_innings, self.off_strike_innings)
            if i and i.batting_state == BatterInningsState.IN_PROGRESS
        ]
        return inningses

    @property
    def overs_bowled(self):
        overs_completed = (self.ball_in_match_innings_num + 1) // 6
        assert overs_completed <= len(self.overs), "overs and balls out of sync"
        return f"{util.balls_to_overs(self.ball_in_match_innings_num)}"

    @property
    def runs_to_win(self) -> Optional[int]:
        if self.target is None:
            return None
        if self.target <= 0:
            return 0
        return max(0, self.target - self.total_runs)

    @property
    def target_reached(self) -> bool:
        if self.runs_to_win is None:
            return False
        return self.runs_to_win == 0

    @property
    def is_complete(self):
        return self.state != InningsState.IN_PROGRESS

    def description(self) -> dict:
        output = {
            "match_innings_num": self.match_innings_num,
            "innings_of": self.batting_team.name,
            "batting_innings_num": self.batting_team_innings_num,
            "target": self.target,
            "start_time": self.start_time,
        }
        return output

    def describe_prev_ball(self) -> Optional[dict]:
        if len(self._ball_events) == 0:
            LOGGER.error(
                "requested previous ball snapshot but there are no " "ball_events"
            )
            return None
        prev_ball: BallCompletedEvent = self._ball_events[-1]
        prev_score: Score = prev_ball.ball_score
        output = {
            "runs": prev_score.total_runs,
            "wickets": prev_score.wickets,
            "runs_off_bat": prev_score.runs_off_bat,
            "extras": prev_score.extra_runs,
            "on_strike": prev_ball.on_strike_player.name,
            "off_strike": prev_ball.off_strike_player.name,
            "bowler": prev_ball.bowler.name,
        }
        return output

    def snapshot(self) -> dict:
        output = {
            "overs": self.overs_bowled,
            "runs": self.runs_scored,
            "wickets": self.wickets_down,
            "runs_to_win": self.runs_to_win,
            "last_ball": self.describe_prev_ball(),
        }
        if self.on_strike_innings:
            output["on_strike"] = self.on_strike_innings.snapshot()
        if self.off_strike_innings:
            output["off_strike"] = self.off_strike_innings.snapshot()
        if self.current_bowler_innings:
            output["bowler"] = self.current_bowler_innings.snapshot()
        if self.current_over:
            output["current_over"] = self.current_over.snapshot()
        return output

    def overview(self):
        output = {"description": self.description(), "snapshot": self.snapshot()}
        batter_status = []
        for batting_innings in self.batter_inningses:
            batter_status.append(batting_innings.overview())
        bowler_status = []
        for bowler_innings in self.bowler_inningses:
            bowler_status.append(bowler_innings.overview())
        over_status = []
        for over in self.overs:
            over_status.append(over.overview())
        output["bowler_inningses"] = bowler_status
        output["batter_inningses"] = batter_status
        output["overs"] = over_status
        return output

    def ascii_status(self):
        resp = f"{self.total_runs}-{self.wickets_down} after {self.overs_bowled}\n\n"
        for i, b_innings in enumerate(
            [self.on_strike_innings, self.off_strike_innings]
        ):
            if not b_innings:
                continue
            resp += f"{b_innings.player}: {b_innings.snapshot()} \n"
        resp += "\n"
        resp += self.current_bowler_innings.snapshot()
        return resp

    def get_batter_innings(self, player: Player) -> "BatterInnings":
        batter_innings = find_innings(player, self.batter_inningses)
        return batter_innings

    def get_bowler_innings(self, player: Player) -> "BowlerInnings":
        bowler_innings = find_innings(player, self.bowler_inningses)
        return bowler_innings

    def get_over_by_number(self, number: int) -> Over:
        # number should be indexed from 0
        return self.overs[number]

    def handle_ball_completed(self, payload: dict) -> dict:
        ball_score = Score.parse(payload["score_text"])
        dismissal = None
        on_strike_player = self.striker
        off_strike_player = self.non_striker
        bowler = self.current_bowler
        dismissal_payload = payload.get("dismissal")
        if dismissal_payload:
            dismissal = parse_dismissal(
                dismissal_payload,
                self,
                on_strike_player,
                off_strike_player,
                bowler,
                self.entity_registrar,
            )
        players_crossed = False
        if ball_score.wide_runs > 0 and ball_score.wide_runs % 2 == 0:
            players_crossed = True
        elif ball_score.ran_runs % 2 == 1:
            players_crossed = True
        bce = BallCompletedEvent(
            on_strike_player,
            off_strike_player,
            bowler,
            ball_score,
            players_crossed,
            dismissal,
        )
        return self.on_ball_completed(bce)

    def handle_batter_innings_started(self, payload: dict) -> dict:
        batter = payload.get("batter")
        if not batter:
            try:
                player = self.next_batter
            except IndexError:
                msg = "cannot process new batter innings as there are no players left"
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        else:
            player = self.entity_registrar.get_entity_data(
                EntityType.PLAYER, payload.get("batter")
            )
        bis = BatterInningsStartedEvent(player)
        return self.on_batter_innings_started(bis)

    def handle_batter_innings_completed(self, payload: dict) -> dict:
        batter = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload.get("batter")
        )
        reason = payload.get("reason", "d")
        state = BatterInningsState(reason)
        bic = BatterInningsCompletedEvent(batter, state)
        return self.on_batter_innings_completed(bic)

    def handle_over_started(self, payload: dict) -> dict:
        if "bowler" not in payload:
            msg = "must specify bowler of new over"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        bowler = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["bowler"]
        )
        if bowler not in self.bowling_lineup:
            msg = f"bowler {bowler} does not play for team {self.bowling_lineup}"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        next_over_num = len(self.overs)
        max_overs_allowed = self.match.max_overs()
        if next_over_num >= max_overs_allowed:
            msg = f"innings already has max number of overs {max_overs_allowed}"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        os = OverStartedEvent(bowler, next_over_num)
        return self.on_over_started(os)

    def handle_over_completed(self, payload: dict) -> dict:
        if "bowler" not in payload:
            bowler = self.current_bowler
        else:
            bowler = self.entity_registrar.get_entity_data(
                EntityType.PLAYER, payload["bowler"]
            )
            if bowler != self.current_bowler:
                msg = (
                    f"OverCompleted event raised for a bowler {bowler} who is "
                    "not the bowler of the most recent over"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.BAD_COMMAND)
        reason_code = payload.get("reason")
        if not reason_code:
            reason = OverState.COMPLETED
        else:
            reason = OverState(reason_code)
        over_number = self.current_over.number
        oce = OverCompletedEvent(over_number, bowler, reason)
        return self.on_over_completed(oce)

    @record_command
    def on_ball_completed(self, bce: BallCompletedEvent) -> dict:
        super().update_score(bce)
        if self._dismissal_pending:
            msg = "received BallCompleted before BatterInningsCompleted while dismissal pending"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        ball_increment = 1 if bce.ball_score.is_valid_delivery() else 0
        self.ball_in_match_innings_num += ball_increment
        self.ball_in_over_num += ball_increment
        self.on_strike_innings.on_ball_completed(bce)
        if bce.dismissal:
            dismissed_innings = find_innings(
                bce.dismissal.batter,
                self.batter_inningses,
            )
            dismissed_innings.on_dismissal(bce.dismissal)
            self._dismissal_pending = True
        self.bowler_innings.on_ball_completed(bce)
        self.current_over.on_ball_completed(bce)
        if bce.players_crossed:
            self.on_strike_innings, self.off_strike_innings = util.switch_strike(
                self.on_strike_innings, self.off_strike_innings
            )
        return self.snapshot()

    @record_command
    def on_batter_innings_started(self, bis: BatterInningsStartedEvent) -> dict:
        if self.on_strike_innings and self.off_strike_innings:
            msg = "there are already two batters at the crease - complete one first"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        try:
            existing = find_innings(bis.batter, self.batter_inningses)
        except ValueError:
            existing = None
        if (
            existing
            and not existing.batting_state != BatterInningsState.RETIRED_NOT_OUT
        ):
            msg = (
                f"batter {existing.batter} has already batted and cannot bat again "
                f"(current state {existing.batting_state})"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        new_innings = BatterInnings(bis.batter, self, len(self.batter_inningses) + 1)
        self.batter_inningses.append(new_innings)
        if not self.on_strike_innings:
            self.on_strike_innings = new_innings
        else:
            self.off_strike_innings = new_innings
        return new_innings.description()

    @record_command
    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent) -> dict:
        if bic.batter not in self.batting_lineup:
            msg = (
                f"batter {bic.batter} is not part of batting team {self.batting_lineup}"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        dismissed_innings = find_innings(bic.batter, self.batter_inningses)
        dismissed_innings.batting_state = bic.batting_state
        if bic.batting_state == BatterInningsState.DISMISSED:
            prev_dismissal = self.previous_ball.dismissal
            if not prev_dismissal:
                msg = (
                    "batter innings completed via dismissal ball event has no "
                    "associated dismissal"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
            elif prev_dismissal.batter != bic.batter:
                msg = (
                    f"batter dismissed in previous ball: {prev_dismissal.batter} "
                    f"does not equal batter whose innings has just completed: {bic.batter}"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.BAD_COMMAND)
            if dismissed_innings.batting_state != BatterInningsState.DISMISSED:
                msg = (
                    f"batter innings completed via a dismissal but batter is "
                    f"currently in state: {dismissed_innings.batting_state}"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.INCONSISTENT_STATE)
        if dismissed_innings == self.on_strike_innings:
            self.on_strike_innings = None
        else:
            self.off_strike_innings = None
        self._dismissal_pending = False
        return dismissed_innings.overview()

    @record_command
    def on_over_completed(self, oc: OverCompletedEvent) -> dict:
        self.on_strike_innings, self.off_strike_innings = util.switch_strike(
            self.on_strike_innings, self.off_strike_innings
        )
        self.current_over.on_over_completed(oc)
        self.current_bowler_innings.on_over_completed(oc)
        return self.current_over.overview()

    @record_command
    def on_over_started(self, os: OverStartedEvent) -> dict:
        if os.bowler == self.current_bowler:
            msg = f"bowler {os.bowler} cannot bowl two overs in a row"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if self.current_over.state == OverState.IN_PROGRESS:
            msg = (
                "Existing over has not yet completed. Send an "
                "OverCompleted event before sending an OverStarted event"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        new_over = Over(os.number, os.bowler, self)
        self.overs.append(new_over)
        try:
            bowler_innings = find_innings(os.bowler, self.bowler_inningses)
        except ValueError:
            bowler_innings = BowlerInnings(
                os.bowler, new_over, self, len(self.bowler_inningses) + 1
            )
            self.bowler_inningses.append(bowler_innings)
        if bowler_innings.overs_completed == self.match.max_bowler_overs:
            msg = (
                f"bowler {os.bowler} has already bowled their full "
                f"allotment of overs"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        self.bowler_innings = bowler_innings
        bowler_innings.on_over_started(os)
        return new_over.description()

    def terminate(self, ice: InningsCompletedEvent):
        if ice.reason == InningsState.ALL_OUT:
            if len(self.yet_to_bat) != 0:
                msg = f"there are still batters remaining so cannot end the innings for reason: {ice.reason}"
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
            if len(self.active_batter_inningses) > 1:
                msg = (
                    f"there are still two batters at the crease, cannot end innings "
                    f"without terminating one first."
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if ice.reason == InningsState.OVERS_COMPLETE:
            if len(self.overs) != self.match.max_overs():
                msg = (
                    f"the allotted number of overs has not been bowled so cannot end "
                    f"the innings for reason {ice.reason}"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        if ice.reason == InningsState.TARGET_REACHED:
            if not self.target or self.total_runs < self.target:
                msg = (
                    f"there is either no valid target that can be "
                    f"reached in this innings or the target has not been reached, "
                    f"so cannot end the innings for reason {ice.reason}. "
                    f"target={self.target} current_score={self.total_runs}"
                )
                LOGGER.warning(msg)
                raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        self.state = ice.reason
        self.end_time = ice.end_time
        for innings in self.active_batter_inningses:
            bic_payload = {
                "batter": str(innings.player),
                "reason": BatterInningsState.INNINGS_COMPLETE.value,
            }
            self.handle_batter_innings_completed(bic_payload)
        if self.current_over.max_balls_bowled:
            reason_code = OverState.COMPLETED.value
        else:
            reason_code = OverState.INNINGS_ENDED.value
        oc_payload = {"reason": reason_code}
        self.handle_over_completed(oc_payload)


class BatterInnings(Context, Scoreable):
    def __init__(self, player: Player, innings: Innings, order_num: int):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.innings = innings
        self.player = player
        self.order_num = order_num
        self.balls = []
        self.dismissal = None
        self.batting_state = BatterInningsState.IN_PROGRESS

    @property
    def balls_faced(self):
        return self._score.valid_deliveries

    def description(self) -> dict:
        output = {
            "batter_name": self.player.name,
            "order_number": self.order_num,
        }
        return output

    def snapshot(self) -> dict:
        output = {
            "name": self.player.name,
            "balls": self.balls_faced,
            "runs": self.runs_scored,
            "fours": self._score.fours,
            "sixes": self._score.sixes,
            "dots": self._score.dots,
        }
        return output

    def overview(self) -> dict:
        output = {
            "description": self.description(),
            "snapshot": self.snapshot(),
            "dismissal": self.dismissal_description(),
        }
        return output

    def dismissal_description(self) -> Optional[dict]:
        if not self.dismissal:
            return None
        fielder_name = ""
        if self.dismissal.fielder:
            fielder_name = self.dismissal.fielder.name
        output = {
            "how_out": self.dismissal.dismissal_type.name,
            "fielder": fielder_name,
            "dismissal_time": self.dismissal.dismissal_time,
        }
        return output

    def on_dismissal(self, dismissal: Dismissal):
        self.dismissal = dismissal
        self.batting_state = BatterInningsState.DISMISSED

    def on_ball_completed(self, bce: BallCompletedEvent):
        super().update_score(bce)

    def ascii_status(self):
        on_strike = self == self.innings.on_strike_innings
        on_strike_token = "*" if on_strike else ""
        resp = f"{self._score.total_runs}{on_strike_token} ({self.balls_faced})"
        return resp


class BowlerInnings(Context, Scoreable):
    def __init__(
        self, player: Player, first_over: Over, innings: Innings, order_num: int
    ):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.innings = innings
        self.player = player
        self.order_num = order_num
        self._overs = [first_over]
        self.wickets = 0
        self.overs_completed = 0

    @property
    def current_over(self) -> Optional[Over]:
        if not self._overs:
            return None
        return self._overs[-1]

    def description(self) -> dict:
        return {
            "bowler_name": self.player.name,
            "order_num": self.order_num,
        }

    def snapshot(self) -> dict:
        return {
            "name": self.player.name,
            "overs": util.balls_to_overs(self.balls_bowled),
            "runs_against_bowler": self._score.runs_against_bowler,
            "wickets": self.wickets,
            "wides": self._score.wide_runs,
            "no_balls": self._score.no_ball_runs,
            "penalty_runs": self._score.penalty_runs,
            "dots": self._score.dots,
        }

    def overview(self) -> dict:
        output = {
            "description": self.description(),
            "snapshot": self.snapshot(),
        }
        overs = []
        for over in self._overs:
            overs.append(over.overview())
        output["overs"] = overs
        return output

    def ascii_status(self):
        resp = (
            f"{self.player}: {self._score.runs_against_bowler}-{self.wickets} "
            f"{util.balls_to_overs(self._score.balls_bowled())}\n"
        )
        return resp

    def on_ball_completed(self, bce: BallCompletedEvent):
        curr_over = self.current_over
        if curr_over.balls_bowled == 6 and bce.ball_score.is_valid_delivery():
            msg = "over has more than 6 legal deliveries"
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        super().update_score(bce)
        if bce.dismissal and bce.dismissal.bowler_accredited():
            self.wickets += 1

    def on_over_completed(self, oce: OverCompletedEvent):
        curr_over = self.current_over
        if curr_over.balls_bowled < 6 and oce.reason == OverState.COMPLETED:
            msg = (
                "over cannot have completed with less than 6 legal "
                "deliveries bowled unless the innings ended"
            )
            LOGGER.warning(msg)
            raise EngineError(msg, RejectReason.ILLEGAL_OPERATION)
        self.overs_completed += 1

    def on_over_started(self, ose: OverStartedEvent):
        over = self.innings.get_over_by_number(ose.number)
        self._overs.append(over)


def find_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError("no innings found for player: {player}")
