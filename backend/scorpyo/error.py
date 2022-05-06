import enum


class RejectReason(enum.Enum):
    BAD_COMMAND = "bc"
    INCONSISTENT_STATE = "is"
    ILLEGAL_OPERATION = "io"


class EngineError(BaseException):
    def __init__(self, msg: str, reason: RejectReason):
        self.msg = msg
        self.reason = reason

    def compile(self, event_type: "EventType"):
        message = {
            "reason": self.reason.value,
            "original_event": event_type.value,
            "message": self.msg,
        }
        return message
