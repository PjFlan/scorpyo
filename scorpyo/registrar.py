from collections import defaultdict

from scorpyo.fixed_data import Entity
from scorpyo.player import Player
from scorpyo.team import Team


class FixedDataRegistrar:
    def __init__(self):
        self._store = defaultdict(list)
        self._id_counter = 0

    def get_fixed_data(self, object_type: Entity, item_reference: any):
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
        self._store[Entity.PLAYER].append(new_player)
        self._id_counter += 1
        return new_player

    def create_team(self, name: str, line_up: list[Player]):
        new_team = Team(self._id_counter, name, line_up)
        self._store[Entity.TEAM].append(new_team)
        self._id_counter += 1
        return new_team

    def get_all_of_type(self, fd_type: Entity):
        return self._store[fd_type]

    def get_from_names(self, fd_type: Entity, names: list[str]):
        fixed_data_items = []
        for name in names:
            fixed_data_items.append(self.get_fixed_data(fd_type, name))
        return fixed_data_items


class EventRegistrar:
    def __init__(self):
        self._events = []

    def add(self, event):
        self._events.append(event)
