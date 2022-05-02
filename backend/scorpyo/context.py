import abc


class Context(abc.ABC):
    def __init__(self):
        self._event_handlers = {}
        self._child_context = None

    @abc.abstractmethod
    def snapshot(self) -> dict:
        pass

    def add_handler(self, event_type: "EventType", func: callable):
        self._event_handlers[event_type] = func

    def handle_event(self, event_type: "EventType", payload: dict) -> dict:
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(payload)
        if not self._child_context:
            raise ValueError(f"no context defined to handle event {event_type}")
        return self._child_context.handle_event(event_type, payload)
