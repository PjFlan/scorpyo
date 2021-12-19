from match import Match
from events import EventType, MatchStartedEvent
from registrar import EventRegistrar, FixedDataRegistrar


class MatchMux:
    def __init__(self, fd_registrar: FixedDataRegistrar):
        self.current_match = None
        self.fd_registrar = fd_registrar
        self.event_registrar = EventRegistrar()

    def on_event(self, event_message: dict):
        event_type = event_message["event_type"]
        payload = event_message["payload"]
        new_event = None
        if event_type == EventType.MATCH_STARTED.value:
            new_event = self.on_new_match(payload, self.fd_registrar)
        elif event_type == EventType.INNINGS_STARTED.value:
            new_event = self.current_match.on_new_innings(payload, self.fd_registrar)
        elif event_type == EventType.BALL_COMPLETED:
            new_event = self.current_match.on_ball_completed(payload, self.fd_registrar)
        elif new_event == EventType.BATTER_INNINGS_COMPLETED:
            new_event = self.current_match.on_batter_innings_completed(
                payload, self.fd_registrar)
        if new_event:
            self.event_registrar.add(new_event)
        else:
            raise ValueError(f"Unrecognised event: {event_type}")

    def on_new_match(self, payload: dict, registrar: FixedDataRegistrar):
        match_started_event = MatchStartedEvent.build(payload, registrar)
        self.current_match = Match(match_started_event)
        return match_started_event
