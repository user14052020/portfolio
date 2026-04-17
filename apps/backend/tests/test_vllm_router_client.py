from app.domain.routing import ROUTING_MODES, RoutingInput, RoutingMode
from app.infrastructure.llm.router_prompt_template_loader import (
    build_router_user_prompt,
    load_router_system_prompt,
)
from app.infrastructure.llm.router_response_schema import ROUTER_DECISION_JSON_SCHEMA
from app.infrastructure.llm.vllm_router_client import VllmRouterClient


def test_router_prompt_includes_required_routing_rules() -> None:
    prompt = load_router_system_prompt(allowed_modes=[mode.value for mode in ROUTING_MODES])

    assert "Allowed modes:" in prompt
    assert "needs_clarification" in prompt
    assert "generation_intent=true only for explicit visualization" in prompt
    assert "continue_existing_flow=true only when the new message clearly continues" in prompt
    assert "should_reset_to_general=true when the previous mode is stale" in prompt
    assert "Return JSON only." in prompt
    assert "Do not include persona prose." in prompt


def test_router_user_prompt_serializes_routing_input() -> None:
    routing_input = RoutingInput(
        user_message="Покажи другой вариант",
        active_mode=RoutingMode.STYLE_EXPLORATION,
        flow_state="completed",
        pending_slots=[],
        recent_messages=["assistant: Попробовать другой стиль?", "user: давай еще"],
        last_ui_action="try_other_style",
        profile_hint_present=True,
    )

    payload = build_router_user_prompt(routing_input=routing_input)

    assert '"user_message": "Покажи другой вариант"' in payload
    assert '"active_mode": "style_exploration"' in payload
    assert '"last_ui_action": "try_other_style"' in payload
    assert '"profile_hint_present": true' in payload


def test_router_schema_declares_core_decision_fields() -> None:
    required = set(ROUTER_DECISION_JSON_SCHEMA["required"])
    properties = ROUTER_DECISION_JSON_SCHEMA["properties"]

    assert ROUTER_DECISION_JSON_SCHEMA["additionalProperties"] is False
    assert "mode" in required
    assert "confidence" in required
    assert "reasoning_depth" in required
    assert properties["mode"]["enum"] == [mode.value for mode in ROUTING_MODES]
    assert properties["missing_slots"]["items"]["type"] == "string"


def test_vllm_router_client_uses_dedicated_router_policy() -> None:
    routing_input = RoutingInput(
        user_message="Что надеть на выставку вечером?",
        active_mode=RoutingMode.GENERAL_ADVICE,
        flow_state="idle",
        pending_slots=[],
        recent_messages=["assistant: Чем помочь?"],
        last_ui_action=None,
        profile_hint_present=False,
    )
    client = VllmRouterClient(
        base_url="http://router.local/v1",
        model="router-model",
        api_key="token",
        timeout_seconds=12.0,
    )

    payload = client._build_payload(routing_input=routing_input)
    timeout = client._build_timeout()

    assert payload["model"] == "router-model"
    assert payload["temperature"] == 0.0
    assert payload["max_tokens"] == VllmRouterClient.ROUTER_MAX_TOKENS
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert timeout.read == 12.0
    assert timeout.connect == VllmRouterClient.ROUTER_CONNECT_TIMEOUT_SECONDS
