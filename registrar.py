from collections import defaultdict
from enum import Enum

from player import Player
from team import Team


class NameableType(Enum):
    PLAYER = 0
    TEAM = 1


class FixedDataRegistrar:

    def __init__(self):
        self._store = defaultdict(list)

    def get_by_name(self, object_type: NameableType, item_name: str):
        search_list = self._store[object_type]
        for test_item in search_list:
            if test_item == item_name:
                return test_item
        raise ValueError(f"No {object_type} found with name {item_name}")

    def get_from_names(self, fd_type: NameableType, names):
        fixed_data_items = []
        for name in names:
            fixed_data = self.get_by_name(fd_type, name)
            fixed_data_items.append(fixed_data)
        return fixed_data_items

    def create_player(self, name: str):
        new_player = Player(name)
        self._store[NameableType.PLAYER].append(new_player)
        return new_player

    def create_team(self, name: str, line_up: list[Player]):
        new_team = Team(name, line_up)
        self._store[NameableType.TEAM].append(new_team)
        return new_team

    def get_players(self):
        return self._store[NameableType.PLAYER]

