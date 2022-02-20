import abc

from scorpyo.events import EventMessageType
from scorpyo.registrar import EntityRegistrar


class Context(abc.ABC):
    entity_registrar = None

    def __init__(self):
        self._event_handlers = {}
        self._child_context = None

    @abc.abstractmethod
    def snapshot(self) -> dict:
        pass

    @abc.abstractmethod
    def status(self) -> dict:
        pass

    @abc.abstractmethod
    def overview(self) -> dict:
        pass

    @classmethod
    def set_entity_registrar(cls, entity_registrar: EntityRegistrar):
        cls.entity_registrar = entity_registrar

    def add_handler(self, event_type: "EventType", func: callable):
        self._event_handlers[event_type] = func

    def handle_event(self, event_type: "EventType", payload: dict) -> EventMessageType:
        handler = self._event_handlers.get(event_type)
        if handler:
            return handler(payload)
        if not self._child_context:
            raise ValueError(f"no context defined to handle event {event_type}")
        return self._child_context.handle_event(event_type, payload)

    def handle_message(
        self, message_type: EventMessageType, context: "Context"
    ) -> EventMessageType:
        # TODO pflanagan: a message handler should know which methods on the context
        # to call in order to build the correct message
        pass
