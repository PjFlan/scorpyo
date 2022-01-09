from collections import defaultdict

from scorpyo.entity import EntityType
from scorpyo.player import Player
from scorpyo.team import Team


class EntityRegistrar:
    def __init__(self):
        self._store = defaultdict(list)
        self._id_counter = 0

    def get_entity_data(self, entity_type: EntityType, item_reference: any):
        if not item_reference:
            return
        search_list = self._store[entity_type]
        lookup = "name" if isinstance(item_reference, str) else "unique_id"
        for test_item in search_list:
            if getattr(test_item, lookup) == item_reference:
                return test_item
        raise ValueError(f"No {entity_type} found with reference {item_reference}")

    def create_player(self, name: str):
        new_player = Player(self._id_counter, name)
        self._store[EntityType.PLAYER].append(new_player)
        self._id_counter += 1
        return new_player

    def create_team(self, name: str):
        new_team = Team(self._id_counter, name)
        self._store[EntityType.TEAM].append(new_team)
        self._id_counter += 1
        return new_team

    def get_all_of_type(self, entity_type: EntityType):
        return self._store[entity_type]

    def get_from_names(self, entity_type: EntityType, names: list[str]):
        entities = []
        for name in names:
            entities.append(self.get_entity_data(entity_type, name))
        return entities


class EventRegistrar:
    def __init__(self):
        self._events = []

    def add(self, event):
        self._events.append(event)
