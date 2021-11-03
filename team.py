from player import Player
from util import FixedData


class Team(FixedData):

    def __init__(self, unique_id: int, name: str, line_up: list[Player]):
        super().__init__(unique_id, name)
        self._line_up = line_up
        self._is_home_team = False

    def add_line_up(self, line_up: list[Player]):
        self._line_up = line_up

    def batter_by_position(self, index):
        return self._line_up[index]

    def get_line_up(self):
        return self._line_up
