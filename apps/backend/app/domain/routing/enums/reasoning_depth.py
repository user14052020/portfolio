from enum import Enum


class ReasoningDepth(str, Enum):
    LIGHT = "light"
    NORMAL = "normal"
    DEEP = "deep"
