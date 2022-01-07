from collections.abc import Sequence
from typing import List

from scorpyo.player import Player
from scorpyo.entity import Entity


class Team(Entity, Sequence):
    def __init__(self, unique_id: int, name: str, line_up: List[Player]):
        super().__init__(unique_id, name)
        self._line_up = line_up
        self._is_home_team = False

    def add_line_up(self, line_up: list[Player]):
        self._line_up = line_up

    def get_line_up(self) -> List[Player]:
        return self._line_up

    def __contains__(self, player: Player) -> bool:
        return player in self._line_up

    def __len__(self) -> int:
        return len(self._line_up)

    def __iter__(self):
        return next(self._line_up)

    def __getitem__(self, item):
        return self._line_up[item]
