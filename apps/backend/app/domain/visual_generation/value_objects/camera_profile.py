from enum import Enum


class CameraProfile(str, Enum):
    TIGHT_OVERHEAD = "tight overhead"
    MEDIUM_FLATLAY = "medium flat lay"
    WIDER_EDITORIAL = "wider editorial overhead"
