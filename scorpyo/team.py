from collections.abc import Sequence
from typing import List

from scorpyo.player import Player
from scorpyo.entity import Entity


class Team(Entity):
    def __init__(self, unique_id: int, name: str):
        super().__init__(unique_id, name)


class MatchTeam(Sequence):
    def __init__(self, match_id: int, team: Team):
        self.match_id = match_id
        self.team = team
        self._lineup: List[Player] = []

    def add_lineup(self, lineup: list[Player]):
        self._lineup = lineup

    def add_player(self, player: Player):
        self._lineup.append(player)

    def get_lineup(self) -> List[Player]:
        return self._lineup

    def __contains__(self, player: Player) -> bool:
        return player in self._lineup

    def __eq__(self, other) -> bool:
        return self.team == other.team

    def __getattr__(self, item):
        team = super().__getattribute__("team")
        return getattr(team, item)

    def __getitem__(self, item):
        return self._lineup[item]

    def __iter__(self):
        return next(self._lineup)

    def __len__(self) -> int:
        return len(self._lineup)
