from enum import Enum


class RouterFailureReason(str, Enum):
    TIMEOUT = "timeout"
    MALFORMED_OUTPUT = "malformed_output"
    VALIDATION_ERROR = "validation_error"
    EMPTY_OUTPUT = "empty_output"
    TRANSPORT_ERROR = "transport_error"
    UNKNOWN = "unknown"
