from __future__ import annotations

from typing import Any

from app.domain.routing import ROUTING_MODES, ReasoningDepth


ROUTER_SCHEMA_NAME = "routing_decision"

ROUTER_DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "mode": {
            "type": "string",
            "enum": [mode.value for mode in ROUTING_MODES],
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
        },
        "needs_clarification": {"type": "boolean"},
        "missing_slots": {
            "type": "array",
            "items": {"type": "string"},
        },
        "generation_intent": {"type": "boolean"},
        "continue_existing_flow": {"type": "boolean"},
        "should_reset_to_general": {"type": "boolean"},
        "reasoning_depth": {
            "type": "string",
            "enum": [depth.value for depth in ReasoningDepth],
        },
        "retrieval_profile": {
            "type": ["string", "null"],
            "enum": ["light", "style_focused", "occasion_focused", "visual_heavy", None],
        },
        "notes": {
            "type": ["string", "null"],
        },
        "requires_style_retrieval": {"type": "boolean"},
        "requires_historical_layer": {"type": "boolean"},
        "requires_stylist_guidance": {"type": "boolean"},
    },
    "required": [
        "mode",
        "confidence",
        "needs_clarification",
        "missing_slots",
        "generation_intent",
        "continue_existing_flow",
        "should_reset_to_general",
        "reasoning_depth",
    ],
}
