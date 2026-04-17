from __future__ import annotations

import json
from collections.abc import Sequence

from app.domain.routing import RoutingInput

from .router_response_schema import ROUTER_DECISION_JSON_SCHEMA


def load_router_system_prompt(*, allowed_modes: Sequence[str]) -> str:
    schema_json = json.dumps(ROUTER_DECISION_JSON_SCHEMA, ensure_ascii=False, separators=(",", ":"))
    modes = ", ".join(allowed_modes)
    return (
        "You are the semantic routing layer for a fashion reasoning assistant. "
        "Your job is scenario classification only. "
        "Never write a user-facing answer. "
        f"Allowed modes: {modes}. "
        "Use clarification_only only when the next step must be a clarification question without starting a full scenario. "
        "Set needs_clarification=true when key information is missing for the most likely scenario. "
        "Set generation_intent=true only for explicit visualization or reference requests, explicit generation UI confirmation, "
        "or a direct request to show or generate an image. "
        "Set continue_existing_flow=true only when the new message clearly continues the active unfinished flow. "
        "Set should_reset_to_general=true when the previous mode is stale, the flow is effectively complete, "
        "or the new message clearly returns to normal conversation. "
        "Keep reasoning_depth light for simple chat, normal for ordinary styling tasks, and deep only for clearly complex reasoning. "
        "Do not include persona prose. "
        "Do not include long fashion knowledge. "
        "Do not include image generation instructions. "
        "Return JSON only. "
        f"JSON schema: {schema_json}"
    )


def build_router_user_prompt(*, routing_input: RoutingInput) -> str:
    payload = routing_input.model_dump(mode="json")
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
