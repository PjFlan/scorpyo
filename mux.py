from match import Match
from events import EventType, MatchStartedEvent
from registrar import FixedDataRegistrar


class MatchMux:

    def __init__(self, registrar: FixedDataRegistrar):
        self.current_match = None
        self._registrar = registrar
        self._events = []

    def on_event(self, event_message: dict):
        event_type = event_message["event_type"]
        payload = event_message["payload"]
        if event_type == EventType.MATCH_STARTED.value:
            self.on_new_match(payload)
        elif event_type == EventType.INNINGS_STARTED.value:
            self.current_match.on_new_innings(payload)

    def on_new_match(self, payload: dict):
        match_started_event = MatchStartedEvent.build(payload, self._registrar)
        self.current_match = Match(match_started_event)
