from enum import Enum


class Nameable(Enum):
    PLAYER = 0
    TEAM = 1


class FixedData:
    name = ""

    def __init__(self, unique_id: int, name: str):
        self.name = name
        self.unique_id = unique_id

    def __eq__(self, other):
        return self.name == other if hasattr(self, "name") else False

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name