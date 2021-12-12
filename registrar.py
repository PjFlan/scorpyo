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
        self._id_counter = 0

    def get_fixed_data(self, object_type: NameableType, item_reference: any):
        if not item_reference:
            return
        search_list = self._store[object_type]
        lookup = "name" if isinstance(item_reference, str) else "unique_id"
        for test_item in search_list:
            if getattr(test_item, lookup) == item_reference:
                return test_item
        raise ValueError(f"No {object_type} found with reference {item_reference}")

    def create_player(self, name: str):
        new_player = Player(self._id_counter, name)
        self._store[NameableType.PLAYER].append(new_player)
        self._id_counter += 1
        return new_player

    def create_team(self, name: str, line_up: list[Player]):
        new_team = Team(self._id_counter, name, line_up)
        self._store[NameableType.TEAM].append(new_team)
        self._id_counter += 1
        return new_team

    def get_all_of_type(self, fd_type: NameableType):
        return self._store[fd_type]

    def get_from_names(self, fd_type: NameableType, names: list[str]):
        fixed_data_items = []
        for name in names:
            fixed_data_items.append(self.get_fixed_data(fd_type, name))
        return fixed_data_items


class EventRegistrar:
    def __init__(self):
        self._events = []

    def add(self, event):
        self._events.append(event)
