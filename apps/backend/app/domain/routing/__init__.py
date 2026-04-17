"""Domain contracts for semantic conversation routing."""

from .entities.conversation_router_context import ConversationRouterContext, RoutingMessageExcerpt
from .entities.routing_decision import RoutingDecision
from .entities.routing_input import RoutingInput
from .enums.reasoning_depth import ReasoningDepth
from .enums.router_failure_reason import RouterFailureReason
from .enums.routing_mode import ROUTING_MODES, RoutingMode

__all__ = [
    "ConversationRouterContext",
    "ROUTING_MODES",
    "ReasoningDepth",
    "RouterFailureReason",
    "RoutingDecision",
    "RoutingInput",
    "RoutingMessageExcerpt",
    "RoutingMode",
]
