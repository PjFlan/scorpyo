import enum


class RejectReason(enum.Enum):
    BAD_COMMAND = "bc"
    INCONSISTENT_STATE = "is"
    ILLEGAL_OPERATION = "io"


class EngineError(BaseException):
    def __init__(self, msg: str, reason: RejectReason):
        self.msg = msg
        self.reason = reason

    def compile(self):
        message = {
            "reject_reason": self.reason.value,
            "message": self.msg,
        }
        return message
