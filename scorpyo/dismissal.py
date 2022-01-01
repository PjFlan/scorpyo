import functools

from scorpyo.fixed_data import Entities
from scorpyo.player import Player
from scorpyo.registrar import FixedDataRegistrar
from scorpyo.static_data.dismissal import DismissalType


def parse_dismissal(
    payload: dict,
    on_strike: Player,
    off_strike: Player,
    bowler: Player,
    registrar: FixedDataRegistrar,
):
    dt = DismissalType.get_from_abbrv(payload["type"])
    if not dt.bowler_accredited and "bowler" in payload:
        raise ValueError(f"dismissal type {dt} should not specify a bowler")
    if not dt.batter_implied and "batter" not in payload:
        raise ValueError(f"dismissal type {dt} must specify batter")
    player_getter = functools.partial(registrar.get_fixed_data, Entities.PLAYER)
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
    return Dismissal(dt, batter, bowler, fielder)


class Dismissal:
    def __init__(
        self,
        dismissal_type: DismissalType,
        batter: Player,
        bowler: Player,
        fielder: Player,
    ):
        self.dismissal_type = dismissal_type
        self.batter = batter
        self.bowler = bowler
        self.fielder = fielder

    def bowler_accredited(self):
        return self.dismissal_type.bowler_accredited
