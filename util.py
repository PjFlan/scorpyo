
class FixedData:

    name = ""

    def __init__(self, unique_id, name):
        self.name = name
        self.unique_id = unique_id

    def __eq__(self, other):
        return self.name == other if hasattr(self, "name") else False

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name
