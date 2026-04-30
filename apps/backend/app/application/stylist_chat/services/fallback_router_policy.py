from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.chat_modes import FlowState
from app.domain.routing import ReasoningDepth, RouterFailureReason, RoutingDecision, RoutingInput, RoutingMode


VISUAL_TRIGGER_MARKERS: tuple[str, ...] = (
    "покажи",
    "сгенерируй",
    "сгенерировать",
    "визуализируй",
    "визуализировать",
    "покажи референс",
    "референс",
    "собери flat lay",
    "flat lay",
    "flatlay",
    "show",
    "generate",
    "visualize",
    "reference",
)

GREETING_MARKERS: tuple[str, ...] = (
    "привет",
    "здравствуй",
    "здравствуйте",
    "добрый день",
    "добрый вечер",
    "доброе утро",
    "hello",
    "hi",
    "hey",
)

GENERAL_PIVOT_MARKERS: tuple[str, ...] = (
    "что ты знаешь",
    "что скажешь",
    "расскажи о",
    "расскажи про",
    "подскажи про",
    "как носить",
    "как сочетать",
    "какой цвет",
    "что думаешь",
    "what do you know",
    "what do you think",
    "tell me about",
    "how to style",
    "how do i wear",
    "can you explain",
)

ACTIVE_CLARIFICATION_STATES: set[str] = {
    FlowState.AWAITING_ANCHOR_GARMENT.value,
    FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION.value,
    FlowState.AWAITING_OCCASION_DETAILS.value,
    FlowState.AWAITING_OCCASION_CLARIFICATION.value,
    FlowState.AWAITING_CLARIFICATION.value,
}


@dataclass(slots=True)
class FallbackRoutingResult:
    decision: RoutingDecision
    matched_rule: str
    failure_reason: RouterFailureReason | None = None


class FallbackRouterPolicy:
    def resolve(
        self,
        *,
        routing_input: RoutingInput,
        failure_reason: RouterFailureReason | None = None,
    ) -> FallbackRoutingResult:
        if routing_input.last_ui_action == "try_other_style":
            return FallbackRoutingResult(
                decision=RoutingDecision(
                    mode=self._prefer_mode(
                        preferred=RoutingMode.STYLE_EXPLORATION,
                        routing_input=routing_input,
                    ),
                    confidence=0.95,
                    needs_clarification=False,
                    missing_slots=[],
                    generation_intent=True,
                    continue_existing_flow=bool(
                        routing_input.active_mode == RoutingMode.STYLE_EXPLORATION
                        and self._flow_is_active(routing_input.flow_state)
                    ),
                    should_reset_to_general=False,
                    reasoning_depth=ReasoningDepth.NORMAL,
                    notes="fallback: explicit style exploration button",
                ),
                matched_rule="explicit_style_button",
                failure_reason=failure_reason,
            )

        if self._looks_like_general_question_pivot(routing_input):
            return FallbackRoutingResult(
                decision=RoutingDecision(
                    mode=self._prefer_mode(
                        preferred=RoutingMode.GENERAL_ADVICE,
                        routing_input=routing_input,
                    ),
                    confidence=0.84,
                    needs_clarification=False,
                    missing_slots=[],
                    generation_intent=False,
                    continue_existing_flow=False,
                    should_reset_to_general=True,
                    reasoning_depth=ReasoningDepth.NORMAL,
                    notes="fallback: clarification flow interrupted by a new general question",
                ),
                matched_rule="clarification_flow_general_pivot",
                failure_reason=failure_reason,
            )

        if self._has_active_unfinished_clarification_flow(routing_input):
            return FallbackRoutingResult(
                decision=RoutingDecision(
                    mode=self._prefer_mode(
                        preferred=routing_input.active_mode or RoutingMode.CLARIFICATION_ONLY,
                        routing_input=routing_input,
                        fallback=RoutingMode.GENERAL_ADVICE,
                    ),
                    confidence=0.78,
                    needs_clarification=True,
                    missing_slots=self._normalized_pending_slots(routing_input),
                    generation_intent=False,
                    continue_existing_flow=True,
                    should_reset_to_general=False,
                    reasoning_depth=ReasoningDepth.LIGHT,
                    notes="fallback: active unfinished clarification flow",
                ),
                matched_rule="active_unfinished_clarification_flow",
                failure_reason=failure_reason,
            )

        if routing_input.last_ui_action == "confirm_visualization" or self._contains_visual_trigger(
            routing_input.user_message
        ):
            return FallbackRoutingResult(
                decision=RoutingDecision(
                    mode=self._prefer_mode(
                        preferred=routing_input.active_mode or RoutingMode.GENERAL_ADVICE,
                        routing_input=routing_input,
                    ),
                    confidence=0.68,
                    needs_clarification=False,
                    missing_slots=[],
                    generation_intent=True,
                    continue_existing_flow=bool(
                        routing_input.active_mode is not None and self._flow_is_active(routing_input.flow_state)
                    ),
                    should_reset_to_general=False,
                    reasoning_depth=ReasoningDepth.NORMAL,
                    notes="fallback: explicit visualization trigger",
                ),
                matched_rule="explicit_visual_trigger",
                failure_reason=failure_reason,
            )

        if self._is_obvious_greeting(routing_input.user_message):
            return FallbackRoutingResult(
                decision=RoutingDecision(
                    mode=self._prefer_mode(
                        preferred=RoutingMode.GENERAL_ADVICE,
                        routing_input=routing_input,
                    ),
                    confidence=0.72,
                    needs_clarification=False,
                    missing_slots=[],
                    generation_intent=False,
                    continue_existing_flow=False,
                    should_reset_to_general=self._should_reset_to_general(routing_input),
                    reasoning_depth=ReasoningDepth.LIGHT,
                    notes="fallback: obvious greeting",
                ),
                matched_rule="obvious_greeting",
                failure_reason=failure_reason,
            )

        return FallbackRoutingResult(
            decision=RoutingDecision(
                mode=self._prefer_mode(
                    preferred=RoutingMode.GENERAL_ADVICE,
                    routing_input=routing_input,
                ),
                confidence=0.15,
                needs_clarification=False,
                missing_slots=[],
                generation_intent=False,
                continue_existing_flow=False,
                should_reset_to_general=self._should_reset_to_general(routing_input),
                reasoning_depth=ReasoningDepth.LIGHT,
                notes="fallback: safe default general advice",
            ),
            matched_rule="safe_default_general_advice",
            failure_reason=failure_reason,
        )

    def _contains_visual_trigger(self, message: str) -> bool:
        normalized = self._normalize_text(message)
        if not normalized:
            return False
        return any(marker in normalized for marker in VISUAL_TRIGGER_MARKERS)

    def _is_obvious_greeting(self, message: str) -> bool:
        normalized = self._normalize_text(message)
        if not normalized:
            return False
        if normalized in GREETING_MARKERS:
            return True
        words = normalized.split()
        return len(words) <= 3 and any(normalized.startswith(marker) for marker in GREETING_MARKERS)

    def _has_active_unfinished_clarification_flow(self, routing_input: RoutingInput) -> bool:
        flow_state = (routing_input.flow_state or "").strip().lower()
        if flow_state in ACTIVE_CLARIFICATION_STATES:
            return True
        return bool(self._normalized_pending_slots(routing_input))

    def _looks_like_general_question_pivot(self, routing_input: RoutingInput) -> bool:
        if not self._has_active_unfinished_clarification_flow(routing_input):
            return False
        normalized = self._normalize_text(routing_input.user_message)
        if not normalized:
            return False
        if any(marker in normalized for marker in GENERAL_PIVOT_MARKERS):
            return True
        question_words = (
            "что ",
            "как ",
            "почему ",
            "зачем ",
            "можно ",
            "какой ",
            "какая ",
            "какие ",
            "расскажи ",
            "подскажи ",
            "what ",
            "how ",
            "why ",
            "can ",
            "tell ",
        )
        return "?" in routing_input.user_message and normalized.startswith(question_words)

    def _normalized_pending_slots(self, routing_input: RoutingInput) -> list[str]:
        result: list[str] = []
        for slot in routing_input.pending_slots:
            cleaned = slot.strip()
            if not cleaned or cleaned in result:
                continue
            result.append(cleaned)
        return result

    def _should_reset_to_general(self, routing_input: RoutingInput) -> bool:
        return bool(
            routing_input.active_mode is not None
            and routing_input.active_mode != RoutingMode.GENERAL_ADVICE
            and not self._has_active_unfinished_clarification_flow(routing_input)
        )

    def _flow_is_active(self, flow_state: str | None) -> bool:
        normalized = (flow_state or "").strip().lower()
        return bool(normalized and normalized not in {FlowState.IDLE.value, FlowState.COMPLETED.value})

    def _prefer_mode(
        self,
        *,
        preferred: RoutingMode,
        routing_input: RoutingInput,
        fallback: RoutingMode = RoutingMode.GENERAL_ADVICE,
    ) -> RoutingMode:
        allowed_modes: list[RoutingMode] = []
        for mode in routing_input.allowed_modes:
            if isinstance(mode, RoutingMode):
                if mode not in allowed_modes:
                    allowed_modes.append(mode)
                continue
            try:
                coerced = RoutingMode(str(mode).strip().lower())
            except ValueError:
                continue
            if coerced not in allowed_modes:
                allowed_modes.append(coerced)
        if not allowed_modes:
            return preferred
        if preferred in allowed_modes:
            return preferred
        if fallback in allowed_modes:
            return fallback
        return allowed_modes[0]

    def _normalize_text(self, message: str) -> str:
        lowered = message.strip().lower()
        lowered = re.sub(r"[!?,.;:]+", " ", lowered)
        return re.sub(r"\s+", " ", lowered).strip()
