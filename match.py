from events import MatchStartedEvent


class Match:

    def __init__(self, match_started_event: MatchStartedEvent):
        self.match_id = match_started_event.match_id
        self.start_time = match_started_event.start_time
        self.match_type = match_started_event.match_type
        self.home_team = match_started_event.home_team
        self.away_team = match_started_event.away_team
        self.match_innings = []

    def get_num_overs(self):
        return self.match_type.overs

    def get_num_innings(self):
        return self.match_type.innings
