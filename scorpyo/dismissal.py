import functools
import time

from scorpyo.entity import EntityType
from scorpyo.entity import Player
from scorpyo.registrar import EntityRegistrar
from scorpyo.static_data.dismissal import get_dismissal_type, DismissalType
from scorpyo.util import get_current_time


def parse_dismissal(
    payload: dict,
    on_strike: Player,
    off_strike: Player,
    bowler: Player,
    registrar: EntityRegistrar,
):
    dt = get_dismissal_type(payload["type"])
    if not dt.bowler_accredited and "bowler" in payload:
        raise ValueError(f"dismissal type {dt} should not specify a bowler")
    if not dt.batter_implied and "batter" not in payload:
        raise ValueError(f"dismissal type {dt} must specify batter")
    player_getter = functools.partial(registrar.get_entity_data, EntityType.PLAYER)
    payload_batter = player_getter(payload.get("batter"))
    payload_bowler = player_getter(payload.get("bowler"))
    fielder = player_getter(payload.get("fielder"))
    if payload_batter and payload_batter not in [off_strike, on_strike]:
        raise ValueError(
            f"batter specified in dismissal {dt}: {payload_batter} is not "
            f"currently at the crease."
        )
    batter = payload_batter if payload_batter else on_strike
    bowler = payload_bowler if payload_bowler else bowler
    if dt.batter_implied and not batter == on_strike:
        raise ValueError(
            f"batter specified in dismissal {dt} is not consistent "
            f"with current striker: {on_strike}"
        )
    if dt.needs_fielder and not fielder:
        raise ValueError(
            f"dismissal type {dt} needs an associated fielder but "
            f"none was specified"
        )
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

    def bowler_accredited(self):
        return self.dismissal_type.bowler_accredited
