from app.application.stylist_chat.services.routing_decision_validator import RoutingDecisionValidator
from app.domain.routing import (
    ROUTING_MODES,
    RouterFailureReason,
    RoutingInput,
    RoutingMode,
)


def test_routing_decision_validator_normalizes_enums_and_trims_extras() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(
        user_message="Покажи вариант на вечер",
        allowed_modes=list(ROUTING_MODES),
    )

    result = validator.validate(
        raw_payload={
            "mode": " STYLE_EXPLORATION ",
            "confidence": 0.82,
            "needs_clarification": False,
            "missing_slots": [" style_reference ", "style_reference"],
            "generation_intent": True,
            "continue_existing_flow": False,
            "should_reset_to_general": False,
            "reasoning_depth": " NORMAL ",
            "notes": "router ok",
            "unexpected": "trim me",
        },
        routing_input=routing_input,
    )

    assert result.used_fallback is False
    assert result.failure_reason is None
    assert result.decision.mode == RoutingMode.STYLE_EXPLORATION
    assert result.decision.reasoning_depth.value == "normal"
    assert result.decision.missing_slots == ["style_reference"]
    assert result.stripped_fields == ["unexpected"]
    assert "unexpected" not in result.normalized_payload


def test_routing_decision_validator_falls_back_for_disallowed_mode() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(
        user_message="Хочу другой стиль",
        allowed_modes=[RoutingMode.GENERAL_ADVICE],
    )

    result = validator.validate(
        raw_payload={
            "mode": "style_exploration",
            "confidence": 0.9,
            "needs_clarification": False,
            "missing_slots": [],
            "generation_intent": True,
            "continue_existing_flow": False,
            "should_reset_to_general": False,
            "reasoning_depth": "normal",
        },
        routing_input=routing_input,
    )

    assert result.used_fallback is True
    assert result.failure_reason == RouterFailureReason.VALIDATION_ERROR
    assert result.decision.mode == RoutingMode.GENERAL_ADVICE
    assert "mode is not in allowed_modes" in result.validation_errors


def test_routing_decision_validator_falls_back_for_confidence_out_of_range() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(user_message="Привет")

    result = validator.validate(
        raw_payload={
            "mode": "general_advice",
            "confidence": 1.7,
            "needs_clarification": False,
            "missing_slots": [],
            "generation_intent": False,
            "continue_existing_flow": False,
            "should_reset_to_general": True,
            "reasoning_depth": "light",
        },
        routing_input=routing_input,
    )

    assert result.used_fallback is True
    assert result.failure_reason == RouterFailureReason.VALIDATION_ERROR
    assert any("confidence" in error for error in result.validation_errors)


def test_routing_decision_validator_falls_back_for_invalid_missing_slots_type() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(user_message="Что надеть?")

    result = validator.validate(
        raw_payload={
            "mode": "occasion_outfit",
            "confidence": 0.73,
            "needs_clarification": True,
            "missing_slots": "event_type",
            "generation_intent": False,
            "continue_existing_flow": True,
            "should_reset_to_general": False,
            "reasoning_depth": "deep",
        },
        routing_input=routing_input,
    )

    assert result.used_fallback is True
    assert result.failure_reason == RouterFailureReason.VALIDATION_ERROR
    assert any("missing_slots" in error for error in result.validation_errors)


def test_routing_decision_validator_falls_back_for_malformed_payload() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(user_message="Привет")

    result = validator.validate(raw_payload=["not", "a", "dict"], routing_input=routing_input)

    assert result.used_fallback is True
    assert result.failure_reason == RouterFailureReason.MALFORMED_OUTPUT
    assert result.decision.mode == RoutingMode.GENERAL_ADVICE
    assert result.validation_errors == ["router payload must be a JSON object"]


def test_routing_decision_validator_uses_fallback_policy_for_style_button() -> None:
    validator = RoutingDecisionValidator()
    routing_input = RoutingInput(
        user_message="",
        last_ui_action="try_other_style",
        active_mode=RoutingMode.STYLE_EXPLORATION,
        flow_state="completed",
    )

    result = validator.validate(raw_payload=["broken"], routing_input=routing_input)

    assert result.used_fallback is True
    assert result.failure_reason == RouterFailureReason.MALFORMED_OUTPUT
    assert result.fallback_rule == "explicit_style_button"
    assert result.decision.mode == RoutingMode.STYLE_EXPLORATION
    assert result.decision.generation_intent is True
