from collections import Sequence
from enum import Enum
from typing import List


class EntityType(Enum):
    PLAYER = 0
    TEAM = 1


class Entity:
    name = ""

    def __init__(self, unique_id: int, name: str):
        self.name = name
        self.unique_id = unique_id

    def __eq__(self, other):
        return self.name == other if hasattr(self, "name") else False

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class Player(Entity):
    def __init__(self, unique_id: int, name: str):
        super().__init__(unique_id, name)

    def get_scorecard_name(self):
        name_parts = self.name.split(" ")
        initials = [i.upper() for i in name_parts]
        initials_str = ".".join(initials[:-1])
        scorecard_name = f"{initials_str} {name_parts[-1]}"
        return scorecard_name


class Team(Entity):
    def __init__(self, unique_id: int, name: str):
        super().__init__(unique_id, name)


class MatchTeam(Sequence):
    def __init__(self, match_id: int, team: Team):
        self.match_id = match_id
        self.team = team
        self._lineup: List[Player] = []

    @property
    def lineup(self) -> List[Player]:
        return self._lineup

    def add_lineup(self, lineup: list[Player]):
        self._lineup = lineup

    def add_player(self, player: Player):
        self._lineup.append(player)

    def __call__(self):
        return [p.name for p in self._lineup]

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
