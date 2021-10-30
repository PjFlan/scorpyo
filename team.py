from player import Player
from util import Nameable


class Team(Nameable):

    def __init__(self, name: str, line_up: list[Player]):
        self.name = name
        self._line_up = line_up
        self._is_home_team = False

    def add_line_up(self, line_up: list[Player]):
        self._line_up = line_up


