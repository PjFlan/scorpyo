import csv
import os
from collections import defaultdict
from typing import Optional

from scorpyo.entity import EntityType
from scorpyo.entity import Player
from scorpyo.entity import Team


class FileLoaderVisitor:
    def __init__(self, entity_config: dict):
        self.source_dir = entity_config["source"]

    def visit_player(self) -> list[Player]:
        file_source = os.path.join(self.source_dir, "player.csv")
        players = []
        with open(file_source, newline="") as fh:
            reader = csv.reader(fh)
            id_counter = 0
            for row in reader:
                name = row[0]
                new_player = Player(id_counter, name)
                players.append(new_player)
                id_counter += 1
        return players

    def visit_team(self) -> list[Team]:
        file_source = os.path.join(self.source_dir, "team.csv")
        teams = []
        with open(file_source, newline="") as fh:
            reader = csv.reader(fh)
            id_counter = 0
            for row in reader:
                name = row[0]
                new_team = Team(id_counter, name)
                teams.append(new_team)
                id_counter += 1
        return teams


class EntityRegistrar:
    def __init__(self, entities_config: dict):
        self.config = entities_config
        self._store = defaultdict(list)
        self._id_counter = 0
        self.load_entities()

    def load_entities(self):
        loader_klass = {"file": FileLoaderVisitor}[self.config["loader"]]
        loader_visitor = loader_klass(self.config)
        for entity in EntityType:
            func_name = f"visit_{entity.name.lower()}"
            func = getattr(loader_visitor, func_name)
            entities = func()
            self._store[entity] = entities

    def get_entity_data(
        self, entity_type: EntityType, item_reference: any
    ) -> Optional[Player]:
        if item_reference is None:
            return None
        search_list = self._store[entity_type]
        lookup = "name" if isinstance(item_reference, str) else "unique_id"
        for candidate in search_list:
            entity = getattr(candidate, lookup)
            if lookup == "name":
                entity = entity.upper()
                item_reference = item_reference.upper()
            if entity == item_reference:
                return candidate
        raise ValueError(f"No {entity_type} found with reference {item_reference}")

    def get_all_of_type(self, entity_type: EntityType):
        return self._store[entity_type]

    def get_from_names(self, entity_type: EntityType, names: list[str]):
        entities = []
        for name in names:
            entities.append(self.get_entity_data(entity_type, name))
        return entities


class EventRegistrar:
    def __init__(self):
        self._store = []

    def add(self, event):
        self._store.append(event)

    def peek(self):
        if len(self._store) > 0:
            return self._store[-1]
        return None
