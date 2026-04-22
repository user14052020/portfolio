import unittest
from datetime import UTC, datetime

from app.domain.interaction_throttle import THROTTLE_ACTION_MESSAGE, ThrottleDecision
from app.domain.usage_access_policy import (
    USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT,
    UsageDecision,
    UserContext,
)
from app.infrastructure.observability.runtime_policy_observability import (
    build_runtime_cooldown_event_payload,
    build_runtime_cooldown_metric_tags,
    build_runtime_usage_access_event_payload,
    build_runtime_usage_access_metric_tags,
)


class RuntimePolicyObservabilityTests(unittest.TestCase):
    def test_usage_access_event_payload_logs_allowed_and_remaining_limits(self) -> None:
        subject = UserContext(subject_id="session:abc", session_id="abc", is_admin=False)
        decision = UsageDecision(
            is_allowed=True,
            denial_reason=None,
            remaining_generations=4,
            remaining_chat_seconds=540,
        )

        payload = build_runtime_usage_access_event_payload(
            subject=subject,
            action_type="text_chat",
            decision=decision,
            surface="stylist_message",
        )
        tags = build_runtime_usage_access_metric_tags(payload)

        self.assertTrue(payload["allowed"])
        self.assertEqual(payload["decision"], "allowed")
        self.assertEqual(payload["remaining_generations"], 4)
        self.assertEqual(payload["remaining_chat_seconds"], 540)
        self.assertEqual(tags["allowed"], True)
        self.assertEqual(tags["denial_reason"], "none")

    def test_usage_access_event_payload_logs_denied_reason(self) -> None:
        subject = UserContext(subject_id="session:abc", session_id="abc", is_admin=False)
        decision = UsageDecision(
            is_allowed=False,
            denial_reason=USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT,
            remaining_generations=4,
            remaining_chat_seconds=0,
        )

        payload = build_runtime_usage_access_event_payload(
            subject=subject,
            action_type="text_chat",
            decision=decision,
            surface="stylist_message",
        )

        self.assertFalse(payload["allowed"])
        self.assertEqual(payload["decision"], "denied")
        self.assertEqual(payload["denial_reason"], USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT)
        self.assertEqual(payload["remaining_chat_seconds"], 0)

    def test_cooldown_event_payload_logs_active_cooldown(self) -> None:
        next_allowed_at = datetime(2026, 4, 19, 10, 30, tzinfo=UTC)
        decision = ThrottleDecision(
            is_allowed=False,
            action_type=THROTTLE_ACTION_MESSAGE,
            retry_after_seconds=25,
            next_allowed_at=next_allowed_at,
            cooldown_seconds=60,
        )

        payload = build_runtime_cooldown_event_payload(
            subject_id="session:abc",
            decision=decision,
            surface="stylist_message",
        )
        tags = build_runtime_cooldown_metric_tags(payload)

        self.assertFalse(payload["allowed"])
        self.assertTrue(payload["cooldown_active"])
        self.assertEqual(payload["retry_after_seconds"], 25)
        self.assertEqual(payload["next_allowed_at"], next_allowed_at.isoformat())
        self.assertEqual(tags["cooldown_active"], True)


if __name__ == "__main__":
    unittest.main()
