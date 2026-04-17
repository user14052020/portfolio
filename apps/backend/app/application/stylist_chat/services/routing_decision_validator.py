from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from app.application.stylist_chat.contracts.ports import (
    RouterSchemaValidatorPort,
)
from app.domain.routing import (
    ROUTING_MODES,
    ReasoningDepth,
    RouterFailureReason,
    RoutingDecision,
    RoutingInput,
    RoutingMode,
)
from app.infrastructure.llm.router_json_schema_validator import RouterJsonSchemaValidator
from .fallback_router_policy import FallbackRouterPolicy


@dataclass(slots=True)
class RoutingDecisionValidationResult:
    decision: RoutingDecision
    normalized_payload: dict[str, Any] = field(default_factory=dict)
    validation_errors: list[str] = field(default_factory=list)
    stripped_fields: list[str] = field(default_factory=list)
    used_fallback: bool = False
    failure_reason: RouterFailureReason | None = None
    fallback_rule: str | None = None


class RoutingDecisionValidator:
    def __init__(
        self,
        *,
        schema_validator: RouterSchemaValidatorPort | None = None,
        fallback_policy: FallbackRouterPolicy | None = None,
    ) -> None:
        self.schema_validator = schema_validator or RouterJsonSchemaValidator()
        self.fallback_policy = fallback_policy or FallbackRouterPolicy()

    def validate(
        self,
        *,
        raw_payload: Any,
        routing_input: RoutingInput,
    ) -> RoutingDecisionValidationResult:
        if not isinstance(raw_payload, dict):
            return self._fallback_result(
                errors=["router payload must be a JSON object"],
                reason=RouterFailureReason.MALFORMED_OUTPUT,
                routing_input=routing_input,
            )

        trimmed_payload = dict(raw_payload)
        stripped_fields = [
            key
            for key in raw_payload.keys()
            if key not in self._allowed_schema_fields()
        ]

        normalized_payload = {
            key: value
            for key, value in trimmed_payload.items()
            if key not in stripped_fields
        }
        normalization_errors: list[str] = []

        normalized_mode = self._normalize_mode(normalized_payload.get("mode"))
        if normalized_mode is None:
            normalization_errors.append("mode is invalid")
        else:
            normalized_payload["mode"] = normalized_mode

        normalized_depth = self._normalize_reasoning_depth(normalized_payload.get("reasoning_depth"))
        if normalized_depth is None:
            normalization_errors.append("reasoning_depth is invalid")
        else:
            normalized_payload["reasoning_depth"] = normalized_depth

        schema_result = self.schema_validator.validate(payload=normalized_payload)
        validation_errors = [*normalization_errors, *schema_result.errors]

        if not validation_errors:
            allowed_modes = self._normalize_allowed_modes(routing_input=routing_input)
            mode_value = schema_result.payload.get("mode")
            if mode_value not in allowed_modes:
                validation_errors.append("mode is not in allowed_modes")

        if validation_errors:
            return self._fallback_result(
                errors=validation_errors,
                reason=RouterFailureReason.VALIDATION_ERROR,
                routing_input=routing_input,
                stripped_fields=[*stripped_fields, *schema_result.stripped_fields],
                normalized_payload=schema_result.payload,
            )

        try:
            decision = RoutingDecision.model_validate(schema_result.payload)
        except ValidationError as exc:
            return self._fallback_result(
                errors=self._format_pydantic_errors(exc),
                reason=RouterFailureReason.VALIDATION_ERROR,
                routing_input=routing_input,
                stripped_fields=[*stripped_fields, *schema_result.stripped_fields],
                normalized_payload=schema_result.payload,
            )

        decision.missing_slots = self._normalize_missing_slots(decision.missing_slots)
        normalized_dump = decision.model_dump(mode="json")
        return RoutingDecisionValidationResult(
            decision=decision,
            normalized_payload=normalized_dump,
            validation_errors=[],
            stripped_fields=self._deduplicate([*stripped_fields, *schema_result.stripped_fields]),
            used_fallback=False,
            failure_reason=None,
        )

    def _allowed_schema_fields(self) -> set[str]:
        return {
            "mode",
            "confidence",
            "needs_clarification",
            "missing_slots",
            "generation_intent",
            "continue_existing_flow",
            "should_reset_to_general",
            "reasoning_depth",
            "notes",
            "requires_style_retrieval",
            "requires_historical_layer",
            "requires_stylist_guidance",
        }

    def _normalize_mode(self, value: Any) -> str | None:
        if isinstance(value, RoutingMode):
            return value.value
        if not isinstance(value, str):
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        for mode in ROUTING_MODES:
            if cleaned == mode.value:
                return mode.value
        return None

    def _normalize_reasoning_depth(self, value: Any) -> str | None:
        if isinstance(value, ReasoningDepth):
            return value.value
        if not isinstance(value, str):
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        for depth in ReasoningDepth:
            if cleaned == depth.value:
                return depth.value
        return None

    def _normalize_allowed_modes(self, *, routing_input: RoutingInput) -> set[str]:
        allowed_modes = routing_input.allowed_modes or list(ROUTING_MODES)
        return {
            mode.value if isinstance(mode, RoutingMode) else str(mode).strip().lower()
            for mode in allowed_modes
            if str(mode).strip()
        }

    def _normalize_missing_slots(self, slots: list[str]) -> list[str]:
        cleaned_slots: list[str] = []
        for slot in slots:
            cleaned = slot.strip()
            if not cleaned or cleaned in cleaned_slots:
                continue
            cleaned_slots.append(cleaned)
        return cleaned_slots

    def _format_pydantic_errors(self, exc: ValidationError) -> list[str]:
        errors: list[str] = []
        for item in exc.errors():
            location = ".".join(str(part) for part in item.get("loc", ())) or "payload"
            message = str(item.get("msg") or "validation error")
            errors.append(f"{location}: {message}")
        return errors

    def _fallback_result(
        self,
        *,
        errors: list[str],
        reason: RouterFailureReason,
        routing_input: RoutingInput,
        stripped_fields: list[str] | None = None,
        normalized_payload: dict[str, Any] | None = None,
    ) -> RoutingDecisionValidationResult:
        fallback = self.fallback_policy.resolve(
            routing_input=routing_input,
            failure_reason=reason,
        )
        return RoutingDecisionValidationResult(
            decision=fallback.decision,
            normalized_payload=normalized_payload or {},
            validation_errors=errors,
            stripped_fields=self._deduplicate(stripped_fields or []),
            used_fallback=True,
            failure_reason=reason,
            fallback_rule=fallback.matched_rule,
        )

    def _deduplicate(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            cleaned = item.strip()
            if not cleaned or cleaned in result:
                continue
            result.append(cleaned)
        return result
