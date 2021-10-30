
class Nameable:

    name = ""

    def __eq__(self, other):
        matches = self.name == other if hasattr(self, "name") else False
        return matches

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name