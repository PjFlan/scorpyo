from match import Match
from events import (
    EventType,
    MatchStartedEvent,
    BallCompletedEvent,
    InningsStartedEvent,
    BatterInningsCompletedEvent,
    BatterInningsStartedEvent,
)
from registrar import EventRegistrar, FixedDataRegistrar


class MatchEngine:
    def __init__(self, fd_registrar: FixedDataRegistrar):
        self.current_match = None
        self.fd_registrar = fd_registrar
        self.event_registrar = EventRegistrar()

    def on_event(self, event_message: dict):
        event_type = event_message["event_type"]
        payload = event_message["payload"]
        new_event = None
        if event_type == EventType.MATCH_STARTED.value:
            new_event = MatchStartedEvent.build(payload, self.fd_registrar)
            self.current_match = Match(new_event)
        elif event_type == EventType.INNINGS_STARTED.value:
            self.current_match.validate()
            new_event = InningsStartedEvent.build(payload, self.fd_registrar, self)
            self.current_match.on_new_innings(new_event)
        elif event_type == EventType.BALL_COMPLETED.value:
            curr_innings = self.current_match.get_current_innings()
            new_event = BallCompletedEvent.build(
                payload,
                curr_innings.get_striker(),
                curr_innings.get_non_striker(),
                curr_innings.get_current_bowler(),
                self.fd_registrar,
            )
            self.current_match.on_ball_completed(new_event)
        elif new_event == EventType.BATTER_INNINGS_COMPLETE.value:
            new_event = BatterInningsCompletedEvent.build(payload, self.fd_registrar)
            self.current_match.on_batter_innings_completed(new_event)
        elif new_event == EventType.BATTER_INNINGS_STARTED.value:
            new_event = BatterInningsStartedEvent.build(
                payload, self.fd_registrar, self.current_match.get_current_innings()
            )
            self.current_match.on_batter_innings_started(new_event)
        if new_event:
            self.event_registrar.add(new_event)
        else:
            raise ValueError(f"Unrecognised event: {event_type}")
