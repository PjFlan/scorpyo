import enum


class InningsState(enum.Enum):
    IN_PROGRESS = "ip"
    ALL_OUT = "ao"
    OVERS_COMPLETE = "oc"
    DECLARED = "d"
    TARGET_REACHED = "tr"


class BatterInningsState(enum.Enum):
    IN_PROGRESS = "ip"
    RETIRED_OUT = "ro"
    RETIRED_NOT_OUT = "rno"
    DISMISSED = "d"
    INNINGS_COMPLETE = "ic"
