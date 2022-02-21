from __future__ import annotations

import enum
from typing import Optional, List

import scorpyo.util as util
from scorpyo.context import Context, record_event
from scorpyo.dismissal import Dismissal, parse_dismissal
from scorpyo.events import (
    BallCompletedEvent,
    InningsStartedEvent,
    BatterInningsCompletedEvent,
    BatterInningsStartedEvent,
    EventType,
    OverCompletedEvent,
    OverStartedEvent,
    InningsCompletedEvent,
)
from scorpyo.entity import EntityType
from scorpyo.over import Over, OverState
from scorpyo.player import Player
from scorpyo.score import Scoreable, Score


class Innings(Context, Scoreable):
    def __init__(self, ise: InningsStartedEvent, match: "Match"):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.match = match
        self.start_time = ise.start_time
        self.end_time = None
        self.match_innings_num = ise.match_innings_num
        self.batting_team_innings_num = ise.batting_team_innings_num

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
        self.bowler_innings = BowlerInnings(ise.opening_bowler, first_over, self)
        self.on_strike_innings = batter_innings_one = BatterInnings(batter_one, self)
        self.off_strike_innings = batter_innings_two = BatterInnings(batter_two, self)
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
        except IndexError as e:
            raise e
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
    def active_batter_innings(self) -> List[BatterInnings]:
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
        return f"{overs_completed}.{self.ball_in_over_num}"

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

    def description(self) -> dict:
        output = {
            "match_innings_num": self.match_innings_num,
            "innings_of": self.batting_team,
            "batting_innings_num": self.batting_team_innings_num,
            "target": self.target,
        }
        return output

    def snapshot(self) -> dict:
        output = {
            "overs": self.overs_bowled,
            "runs": self.runs_scored,
            "wickets": self.wickets_down,
            "runs_to_win": self.runs_to_win,
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
        # TODO pflanagan: should return batters at the crease, current bowler,
        #  current ball number, total runs, wickets, extras etc.
        resp = f"{self.total_runs}-{self.wickets_down} after {self.overs_bowled}\n\n"
        for i, b_innings in enumerate(
            [self.on_strike_innings, self.off_strike_innings]
        ):
            if not b_innings:
                continue
            resp += f"{b_innings.player}: {b_innings.status()} \n"
        resp += "\n"
        resp += self.current_bowler_innings.status()
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
        dismissal_payload = dismissal = None
        on_strike_player = self.striker
        off_strike_player = self.non_striker
        bowler = self.current_bowler
        for key in payload:
            if key == "on_strike":
                on_strike_player = self.entity_registrar.get_entity_data(
                    EntityType.PLAYER, payload[key]
                )
            elif key == "off_strike":
                off_strike_player = self.entity_registrar.get_entity_data(
                    EntityType.PLAYER, payload[key]
                )
            elif key == "bowler":
                bowler = self.entity_registrar.get_entity_data(
                    EntityType.PLAYER, payload[key]
                )
            elif key == "dismissal":
                dismissal_payload = payload[key]
        if dismissal_payload:
            dismissal = parse_dismissal(
                payload["dismissal"],
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
        batter = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["batter"]
        )
        if not batter:
            try:
                batter = self.next_batter
            except IndexError:
                raise ValueError(
                    "cannot process new batter innings as there are no players left"
                )
        bis = BatterInningsStartedEvent(batter)
        return self.on_batter_innings_started(bis)

    def handle_batter_innings_completed(self, payload: dict) -> dict:
        batter = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["batter"]
        )
        state = BatterInningsState(payload["reason"])
        bic = BatterInningsCompletedEvent(batter, state)
        return self.on_batter_innings_completed(bic)

    def handle_over_completed(self, payload: dict) -> dict:
        if "bowler" not in payload:
            raise ValueError("must specify bowler of completed over")
        bowler = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["bowler"]
        )
        reason = payload.get("reason")
        if not reason:
            raise ValueError(
                "must provide over completion reason when raising an "
                "OverCompleted event"
            )
        try:
            reason = OverState(payload["reason"])
        except KeyError:
            raise ValueError("invalid over completion reason {reason}")
        if bowler != self.current_bowler:
            raise ValueError(
                "OverCompleted event raised for a bowler {bowler} who is "
                "not the bowler of the most recent over"
            )
        over_number = payload["over_num"]
        oc = OverCompletedEvent(over_number, bowler, reason)
        return self.on_over_completed(oc)

    def handle_over_started(self, payload: dict) -> dict:
        if "bowler" not in payload:
            raise ValueError("must specify bowler of new over")
        bowler = self.entity_registrar.get_entity_data(
            EntityType.PLAYER, payload["bowler"]
        )
        if bowler not in self.bowling_lineup:
            raise ValueError(
                f"bowler {bowler} does not play for team {self.bowling_lineup}"
            )
        next_over_num = len(self.overs)
        max_overs_allowed = self.match.max_overs()
        if next_over_num >= max_overs_allowed:
            raise ValueError(
                f"innings already has max number of overs {max_overs_allowed}"
            )
        os = OverStartedEvent(bowler, next_over_num)
        return self.on_over_started(os)

    @record_event
    def on_ball_completed(self, bce: BallCompletedEvent) -> dict:
        super().update_score(bce)
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
        self.bowler_innings.on_ball_completed(bce)
        self.current_over.on_ball_completed(bce)
        if bce.players_crossed:
            self.on_strike_innings, self.off_strike_innings = util.switch_strike(
                self.on_strike_innings, self.off_strike_innings
            )
        return self.snapshot()

    @record_event
    def on_batter_innings_started(self, bis: BatterInningsStartedEvent) -> dict:
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
        return new_innings.description()

    @record_event
    def on_batter_innings_completed(self, bic: BatterInningsCompletedEvent) -> dict:
        if bic.batter not in self.batting_lineup:
            raise ValueError(
                "batter {bic.batter} is not part of batting team {"
                "self.batting_lineup}"
            )
        dismissed_innings = find_innings(bic.batter, self.batter_inningses)
        if bic.batting_state == BatterInningsState.DISMISSED:
            prev_dismissal = self.previous_ball.dismissal
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
        return dismissed_innings.overview()

    @record_event
    def on_over_completed(self, oc: OverCompletedEvent) -> dict:
        self.on_strike_innings, self.off_strike_innings = util.switch_strike(
            self.on_strike_innings, self.off_strike_innings
        )
        self.current_over.on_over_completed(oc)
        self.current_bowler_innings.on_over_completed(oc)
        return self.current_over.overview()

    @record_event
    def on_over_started(self, os: OverStartedEvent) -> dict:
        if os.bowler == self.current_bowler:
            raise ValueError("bowler {player} cannot bowl two overs in a row")
        if self.current_over.state == OverState.IN_PROGRESS:
            raise ValueError(
                "Existing over has not yet completed. Send an "
                "OverCompleted event before sending an OverStarted event"
            )
        new_over = Over(os.over_number, os.bowler, self)
        self.overs.append(new_over)
        try:
            bowler_innings = find_innings(os.bowler, self.bowler_inningses)
        except ValueError:
            bowler_innings = BowlerInnings(os.bowler, new_over, self)
            self.bowler_inningses.append(bowler_innings)
        if bowler_innings.overs_completed == self.match.max_bowler_overs:
            raise ValueError(
                f"bowler {os.bowler} has already bowled their full "
                f"allotment of overs"
            )
        self.bowler_innings = bowler_innings
        bowler_innings.on_over_started(os)
        return new_over.description()

    def terminate(self, ice: InningsCompletedEvent):
        if ice.reason == InningsState.ALL_OUT:
            assert len(self.yet_to_bat) == 0, (
                f"there are still batters remaining so cannot end the "
                f"innings for reason: {ice.reason}"
            )
            assert len(self.active_batter_innings) <= 1, (
                f"there are still two batters at the crease, so cannot end "
                f"the innings for reason {ice.reason} without terminating one of the "
                f"batter inningses first."
            )
        if ice.reason == InningsState.OVERS_COMPLETE:
            assert len(self.overs) == self.match.max_overs(), (
                f"the allotted number of overs has not been bowled so cannot "
                f"end the innings for reason {ice.reason}"
            )
        if ice.reason == InningsState.TARGET_REACHED:
            if not self.target or self.total_runs < self.target:
                raise AssertionError(
                    f"there is either no valid target that can be "
                    f"reached in this innings or the target has not "
                    f"been reached, so cannot end the innings for "
                    f"reason {ice.reason}. target={self.target} current_score="
                    f"{self.total_runs}"
                )
        self.state = ice.reason
        self.end_time = ice.end_time
        for innings in self.active_batter_innings:
            # TODO pflanagan: there should be some sort of mechanism for raising
            #  events internally so that the context objects need not know which
            #  exact handler to use, and instead the message can flow through the
            #  natural context hierarchy from top down
            payload = {
                "batter": str(innings.player),
                "reason": BatterInningsState.INNINGS_COMPLETE.value,
            }
            self.handle_batter_innings_completed(payload)


class BatterInnings(Context, Scoreable):
    def __init__(self, player: Player, innings: Innings):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.innings = innings
        self.player = player
        self.balls = []
        self.dismissal = None
        self.batting_state = BatterInningsState.IN_PROGRESS

    @property
    def balls_faced(self):
        return self._score.valid_deliveries

    def description(self) -> dict:
        return {}

    def snapshot(self) -> dict:
        return {}

    def overview(self) -> dict:
        output = {
            "description": self.description(),
            "snapshot": self.snapshot(),
            "dismissal": self.dismissal_description(),
        }
        # needs to return dismissal description where applicable
        return {}

    def dismissal_description(self) -> dict:
        return {}

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
    def __init__(self, player: Player, first_over: Over, innings: Innings):
        Context.__init__(self)
        Scoreable.__init__(self)
        self.innings = innings
        self.player = player
        self._overs = [first_over]
        self.wickets = 0
        self.overs_completed = 0

    @property
    def runs_against(self):
        return self._score.runs_off_bat + self._score.bowler_extras

    @property
    def current_over(self) -> Optional[Over]:
        if not self._overs:
            return None
        return self._overs[-1]

    def description(self) -> dict:
        return {}

    def snapshot(self) -> dict:
        return {}

    def overview(self) -> dict:
        output = {
            "description": self.description(),
            "snapshot": self.snapshot(),
        }
        return {}

    def ascii_status(self):
        balls_in_over = self._score.valid_deliveries % 6
        overs_completed = self._score.valid_deliveries // 6
        assert overs_completed >= self.overs_completed, (
            "bowler overs out of sync " "with balls"
        )
        resp = (
            f"{self.player}: {self.runs_against}-{self.wickets} "
            f"({self.overs_completed}.{balls_in_over})\n"
        )
        return resp

    def on_ball_completed(self, bce: BallCompletedEvent):
        curr_over = self.current_over
        if curr_over.balls_bowled == 6 and bce.ball_score.is_valid_delivery():
            raise ValueError("over has more than 6 legal deliveries")
        super().update_score(bce)
        if bce.dismissal and bce.dismissal.bowler_accredited():
            self.wickets += 1

    def on_over_completed(self, oc: OverCompletedEvent):
        curr_over = self.current_over
        if curr_over.balls_bowled < 6 and oc.reason == OverState.COMPLETED:
            raise ValueError(
                "over cannot have completed with less than 6 legal "
                " deliveries bowled unless the innings ended"
            )
        self.overs_completed += 1

    def on_over_started(self, os: OverStartedEvent):
        over = self.innings.get_over_by_number(os.over_number)
        self._overs.append(over)


class InningsState(enum.Enum):
    IN_PROGRESS = "ip"
    ALL_OUT = "ao"
    OVERS_COMPLETE = "oc"
    DECLARED = "d"
    TARGET_REACHED = "tr"


class BatterInningsState(enum.Enum):
    IN_PROGRESS = "ip"
    RETIRED_OUT = "ro"
    RETIRED_NOT_OUT = "rno"
    DISMISSED = "d"
    INNINGS_COMPLETE = "ic"


def find_innings(player: Player, inningses: list):
    for innings in inningses:
        if innings.player == player:
            return innings
    raise ValueError(f"no innings found for player: {player}")
