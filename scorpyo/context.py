import abc
from functools import wraps

from scorpyo.registrar import EntityRegistrar, EventRegistrar


def record_event(func: callable):
    @wraps(func)
    def wrapper(*args, **kwargs):
        event_registrar = Context.assure_event_registrar()
        event_registrar.add(args[1])  # first arg would be self
        return func(*args, **kwargs)

    return wrapper


class Context(abc.ABC):
    entity_registrar = None
    event_registrar = None

    def __init__(self):
        self._event_handlers = {}
        self._child_context = None

    @abc.abstractmethod
    def snapshot(self) -> dict:
        pass

    @classmethod
    def assure_entity_registrar(cls) -> EntityRegistrar:
        if cls.entity_registrar:
            return cls.entity_registrar
        cls.entity_registrar = EntityRegistrar()
        return cls.entity_registrar

    @classmethod
    def assure_event_registrar(cls) -> EventRegistrar:
        if cls.event_registrar:
            return cls.event_registrar
        cls.event_registrar = EventRegistrar()
        return cls.event_registrar

    def add_handler(self, event_type: "EventType", func: callable):
        self._event_handlers[event_type] = func

    def handle_event(self, event_type: "EventType", payload: dict) -> dict:
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(payload)
        if not self._child_context:
            raise ValueError(f"no context defined to handle event {event_type}")
        return self._child_context.handle_event(event_type, payload)
