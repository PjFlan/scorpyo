from util import Nameable


class Player(Nameable):

    def __init__(self, name):
        self.name = name

    def get_scorecard_name(self):
        name_parts = self.name.split(" ")
        initials = [i.upper() for i in name_parts]
        initials_str = ".".join(initials[:-1])
        scorecard_name = f"{initials_str} {name_parts[-1]}"
        return scorecard_name
