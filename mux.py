from match import Match
from events import EventType, MatchStartedEvent
from registrar import FixedDataRegistrar


class MatchMux:

    def __init__(self, registrar: FixedDataRegistrar):
        self.current_match = None
        self._registrar = registrar

    def on_event(self, event_message: dict):
        event_type = event_message["event_type"]
        if event_type == EventType.MATCH_STARTED.value:
            self.on_new_match(event_message["payload"])

    def on_new_match(self, payload: dict):
        match_started_event = MatchStartedEvent.build(payload, self._registrar)
        self.current_match = Match(match_started_event)

