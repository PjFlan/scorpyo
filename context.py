from events import EventType
from registrar import FixedDataRegistrar


class Context:
    fd_registrar = None

    def __init__(self):
        self._handlers = {}
        self._child_context = None

    # TODO: fd_registrar should be implemented as a service
    @classmethod
    def set_fd_registrar(cls, fd_registrar: FixedDataRegistrar):
        cls.fd_registrar = fd_registrar

    def add_handler(self, event_type: EventType, func: callable):
        self._handlers[event_type] = func

    def handle_event(self, event_type: EventType, payload: dict):
        handler = self._handlers.get(event_type)
        if handler:
            return handler(payload)
        if not self._child_context:
            raise ValueError(f"no context defined to handle event {event_type}")
        return self._child_context.handle_event(event_type)
