from __future__ import annotations

from typing import Any

from app.domain.interaction_throttle import ThrottleDecision
from app.domain.usage_access_policy import RequestedActionType, UsageDecision, UserContext
from app.infrastructure.observability.structured_event_logger import StructuredEventLogger
from app.infrastructure.observability.structured_metrics_recorder import StructuredMetricsRecorder


def build_runtime_usage_access_event_payload(
    *,
    subject: UserContext,
    action_type: RequestedActionType,
    decision: UsageDecision,
    surface: str,
) -> dict[str, Any]:
    return {
        "surface": surface,
        "subject_id": subject.subject_id,
        "session_id": subject.session_id,
        "user_id": subject.user_id,
        "is_admin": subject.is_admin,
        "action_type": action_type,
        "allowed": decision.is_allowed,
        "decision": "allowed" if decision.is_allowed else "denied",
        "denial_reason": decision.denial_reason,
        "remaining_generations": decision.remaining_generations,
        "remaining_chat_seconds": decision.remaining_chat_seconds,
    }


def build_runtime_usage_access_metric_tags(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface": payload["surface"],
        "action_type": payload["action_type"],
        "allowed": payload["allowed"],
        "denial_reason": payload["denial_reason"] or "none",
        "is_admin": payload["is_admin"],
    }


def build_runtime_cooldown_event_payload(
    *,
    subject_id: str,
    decision: ThrottleDecision,
    surface: str,
) -> dict[str, Any]:
    cooldown_active = not decision.is_allowed
    return {
        "surface": surface,
        "subject_id": subject_id,
        "action_type": decision.action_type,
        "allowed": decision.is_allowed,
        "decision": "allowed" if decision.is_allowed else "denied",
        "cooldown_active": cooldown_active,
        "retry_after_seconds": decision.retry_after_seconds,
        "next_allowed_at": decision.next_allowed_at.isoformat() if decision.next_allowed_at else None,
        "cooldown_seconds": decision.cooldown_seconds,
    }


def build_runtime_cooldown_metric_tags(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "surface": payload["surface"],
        "action_type": payload["action_type"],
        "allowed": payload["allowed"],
        "cooldown_active": payload["cooldown_active"],
    }


class RuntimePolicyObservability:
    def __init__(
        self,
        *,
        event_logger: StructuredEventLogger | None = None,
        metrics_recorder: StructuredMetricsRecorder | None = None,
    ) -> None:
        self.event_logger = event_logger or StructuredEventLogger()
        self.metrics_recorder = metrics_recorder or StructuredMetricsRecorder()

    async def record_usage_access_decision(
        self,
        *,
        subject: UserContext,
        action_type: RequestedActionType,
        decision: UsageDecision,
        surface: str,
    ) -> None:
        payload = build_runtime_usage_access_event_payload(
            subject=subject,
            action_type=action_type,
            decision=decision,
            surface=surface,
        )
        try:
            await self.event_logger.emit("runtime_usage_access_decision", payload)
            await self.metrics_recorder.increment(
                "runtime_usage_access_decisions_total",
                tags=build_runtime_usage_access_metric_tags(payload),
            )
        except Exception:
            return

    async def record_cooldown_decision(
        self,
        *,
        subject_id: str,
        decision: ThrottleDecision,
        surface: str,
    ) -> None:
        payload = build_runtime_cooldown_event_payload(
            subject_id=subject_id,
            decision=decision,
            surface=surface,
        )
        try:
            await self.event_logger.emit("runtime_cooldown_decision", payload)
            await self.metrics_recorder.increment(
                "runtime_cooldown_decisions_total",
                tags=build_runtime_cooldown_metric_tags(payload),
            )
        except Exception:
            return
