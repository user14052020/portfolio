from app.application.stylist_chat.services.fallback_router_policy import FallbackRouterPolicy
from app.domain.routing import RoutingInput, RoutingMode


def test_fallback_router_policy_routes_explicit_style_button_to_style_exploration() -> None:
    policy = FallbackRouterPolicy()

    result = policy.resolve(
        routing_input=RoutingInput(
            user_message="",
            last_ui_action="try_other_style",
            active_mode=RoutingMode.STYLE_EXPLORATION,
            flow_state="completed",
        )
    )

    assert result.matched_rule == "explicit_style_button"
    assert result.decision.mode == RoutingMode.STYLE_EXPLORATION
    assert result.decision.generation_intent is True


def test_fallback_router_policy_routes_active_unfinished_clarification_flow() -> None:
    policy = FallbackRouterPolicy()

    result = policy.resolve(
        routing_input=RoutingInput(
            user_message="не знаю",
            active_mode=RoutingMode.OCCASION_OUTFIT,
            flow_state="awaiting_occasion_details",
            pending_slots=["event_type", "venue"],
        )
    )

    assert result.matched_rule == "active_unfinished_clarification_flow"
    assert result.decision.mode == RoutingMode.OCCASION_OUTFIT
    assert result.decision.needs_clarification is True
    assert result.decision.continue_existing_flow is True
    assert result.decision.missing_slots == ["event_type", "venue"]


def test_fallback_router_policy_detects_explicit_visual_trigger() -> None:
    policy = FallbackRouterPolicy()

    result = policy.resolve(
        routing_input=RoutingInput(
            user_message="Покажи референс, пожалуйста",
            active_mode=RoutingMode.GENERAL_ADVICE,
            flow_state="idle",
        )
    )

    assert result.matched_rule == "explicit_visual_trigger"
    assert result.decision.mode == RoutingMode.GENERAL_ADVICE
    assert result.decision.generation_intent is True


def test_fallback_router_policy_detects_obvious_greeting() -> None:
    policy = FallbackRouterPolicy()

    result = policy.resolve(
        routing_input=RoutingInput(
            user_message="Привет!",
            active_mode=RoutingMode.STYLE_EXPLORATION,
            flow_state="completed",
        )
    )

    assert result.matched_rule == "obvious_greeting"
    assert result.decision.mode == RoutingMode.GENERAL_ADVICE
    assert result.decision.generation_intent is False
    assert result.decision.should_reset_to_general is True


def test_fallback_router_policy_uses_safe_default_general_advice() -> None:
    policy = FallbackRouterPolicy()

    result = policy.resolve(
        routing_input=RoutingInput(
            user_message="мне нравится структура образа",
            active_mode=RoutingMode.GENERAL_ADVICE,
            flow_state="idle",
        )
    )

    assert result.matched_rule == "safe_default_general_advice"
    assert result.decision.mode == RoutingMode.GENERAL_ADVICE
    assert result.decision.generation_intent is False
    assert result.decision.confidence == 0.15
