import enum


class RejectReason(enum.Enum):
    BAD_COMMAND = "bc"
    INCONSISTENT_STATE = "is"
    ILLEGAL_OPERATION = "io"


class AbstractScorpyoError(BaseException):
    def __init__(self, msg: str, reason: RejectReason):
        self.msg = msg
        self.reason = reason

    def compile(self):
        message = {
            "reject_reason": self.reason.value,
            "message": self.msg,
        }
        return message


class ClientError(AbstractScorpyoError):
    def __init__(self, msg: str, reason: RejectReason):
        super().__init__(msg, reason)


class EngineError(AbstractScorpyoError):
    def __init__(self, msg: str, reason: RejectReason):
        super().__init__(msg, reason)
