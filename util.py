import score


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


class Scoreable:
    def __init__(self):
        self._ball_events = []
        self._score = score.Score(0, 0, 0, 0, 0, 0, 0)

    def on_ball_completed(self, ball_completed_event):
        self._ball_events.append(ball_completed_event)
        self._score.add(ball_completed_event.ball_score)

    def get_previous_ball(self):
        if len(self._ball_events) == 0:
            return None
        return self._ball_events[-1]

    def runs_scored(self):
        return self._score.runs_off_bat


def switch_strike(striker, non_striker):
    temp = non_striker
    new_non_striker = striker
    new_striker = temp
    return new_striker, new_non_striker
