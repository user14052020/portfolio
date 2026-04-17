from enum import Enum


class RoutingMode(str, Enum):
    GENERAL_ADVICE = "general_advice"
    GARMENT_MATCHING = "garment_matching"
    STYLE_EXPLORATION = "style_exploration"
    OCCASION_OUTFIT = "occasion_outfit"
    CLARIFICATION_ONLY = "clarification_only"


ROUTING_MODES: tuple[RoutingMode, ...] = (
    RoutingMode.GENERAL_ADVICE,
    RoutingMode.GARMENT_MATCHING,
    RoutingMode.STYLE_EXPLORATION,
    RoutingMode.OCCASION_OUTFIT,
    RoutingMode.CLARIFICATION_ONLY,
)
