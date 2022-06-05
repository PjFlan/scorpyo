import functools
import time

from scorpyo.entity import EntityType
from scorpyo.entity import Player
from scorpyo.error import RejectReason, EngineError
from scorpyo.registrar import EntityRegistrar
from scorpyo.definitions.dismissal import (
    get_dismissal_type,
    DismissalType,
    CAUGHT,
    RUN_OUT,
    BOWLED,
    STUMPED,
    HIT_WICKET,
    TIMED_OUT,
    OBSTRUCTING_FIELD,
    HANDLED_BALL,
)
from scorpyo.util import get_current_time, LOGGER


def parse_dismissal(
    payload: dict,
    innings: "Innings",
    on_strike: Player,
    off_strike: Player,
    bowler: Player,
    registrar: EntityRegistrar,
):
    dt = get_dismissal_type(payload["type"])
    if not dt.bowler_accredited and "bowler" in payload:
        msg = f"dismissal type {dt} should not specify a bowler"
        LOGGER.warning(msg)
        raise EngineError(msg, RejectReason.BAD_COMMAND)
    if not dt.batter_implied and "batter" not in payload:
        msg = f"dismissal type {dt} must specify batter"
        LOGGER.warning(msg)
        raise EngineError(msg, RejectReason.BAD_COMMAND)
    player_getter = functools.partial(registrar.get_entity_data, EntityType.PLAYER)
    payload_batter = player_getter(payload.get("batter"))
    fielder = player_getter(payload.get("fielder"))
    if payload_batter and payload_batter not in [off_strike, on_strike]:
        raise EngineError(
            f"batter specified in dismissal {dt}: {payload_batter} is not "
            f"currently at the crease."
        )
    batter = payload_batter if payload_batter else on_strike
    if dt.batter_implied and not batter == on_strike:
        raise ValueError(
            f"batter specified in dismissal {dt} is not consistent "
            f"with current striker: {on_strike}"
        )
    if dt.needs_fielder:
        if not fielder:
            msg = f"dismissal type {dt} needs an associated fielder but none was specified"
            LOGGER.warn(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
        if fielder not in innings.bowling_lineup:
            msg = f"fielder is not in the bowling team lineup, cannot be attributed to the dismissal"
            LOGGER.warn(msg)
            raise EngineError(msg, RejectReason.BAD_COMMAND)
    return Dismissal(dt, batter, bowler, fielder, get_current_time())


class Dismissal:
    def __init__(
        self,
        dismissal_type: DismissalType,
        batter: Player,
        bowler: Player,
        fielder: Player,
        dismissal_time: time,
    ):
        self.dismissal_type = dismissal_type
        self.batter = batter
        self.bowler = bowler
        self.fielder = fielder
        self.dismissal_time = dismissal_time

    @property
    def bowler_accredited(self):
        return self.dismissal_type.bowler_accredited

    @property
    def scorecard_format(self):
        if self.dismissal_type == CAUGHT:
            return f"c {self.fielder.scorecard_name} b {self.bowler.scorecard_name}"
        elif self.dismissal_type == RUN_OUT:
            return f"run out ({self.bowler.scorecard_name})"
        elif self.dismissal_type == BOWLED:
            return f"b {self.bowler.scorecard_name}"
        elif self.dismissal_type == STUMPED:
            return f"St {self.fielder.scorecard_name} b {self.bowler.scorecard_name}"
        elif self.dismissal_type == HIT_WICKET:
            return f"hit wicket b {self.bowler.scorecard_name}"
        elif self.dismissal_type == TIMED_OUT:
            return f"timed out"
        elif self.dismissal_type == OBSTRUCTING_FIELD:
            return f"obstructing field"
        elif self.dismissal_type == HANDLED_BALL:
            return f"handled ball"
