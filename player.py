from fixed_data import FixedData


class Player(FixedData):
    def __init__(self, unique_id: int, name: str):
        super().__init__(unique_id, name)

    def get_scorecard_name(self):
        name_parts = self.name.split(" ")
        initials = [i.upper() for i in name_parts]
        initials_str = ".".join(initials[:-1])
        scorecard_name = f"{initials_str} {name_parts[-1]}"
        return scorecard_name
