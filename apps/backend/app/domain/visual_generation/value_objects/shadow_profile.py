from enum import Enum


class ShadowProfile(str, Enum):
    SOFT_DIFFUSED = "soft diffused"
    MODERATE_NATURAL = "moderate natural"
    CRISP_EDITORIAL = "crisp editorial"
