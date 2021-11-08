from match import Match
from events import EventType, MatchStartedEvent
from registrar import EventRegistrar, FixedDataRegistrar


class MatchMux:

    def __init__(self, fd_registrar: FixedDataRegistrar):
        self.current_match = None
        self._fd_registrar = fd_registrar
        self._event_registrar = EventRegistrar()

    def on_event(self, event_message: dict):
        event_type = event_message["event_type"]
        payload = event_message["payload"]
        new_event = None
        if event_type == EventType.MATCH_STARTED.value:
            new_event = self.on_new_match(payload)
        elif event_type == EventType.INNINGS_STARTED.value:
            new_event = self.current_match.on_new_innings(payload)
        elif event_type == EventType.BALL_COMPLETED:
            new_event = self.current_match.on_ball_completed()
        if new_event:
            self._event_registrar.add(new_event)
        else:
            raise ValueError(f"Unrecognised event: {event_type}")

    def on_new_match(self, payload: dict):
        match_started_event = MatchStartedEvent.build(payload, self._fd_registrar)
        self.current_match = Match(match_started_event)
        return match_started_event
