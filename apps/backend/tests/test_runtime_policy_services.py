import unittest
from types import SimpleNamespace

from app.domain.interaction_throttle import (
    THROTTLE_ACTION_MESSAGE,
    THROTTLE_ACTION_TRY_OTHER_STYLE,
    ThrottleDecision,
)
from app.domain.stylist_runtime_settings import StylistRuntimeLimits
from app.domain.usage_access_policy import (
    USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT,
    USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
    RequestedAction,
    UserContext,
)
from app.services.interaction_throttle import InteractionThrottleService
from app.services.runtime_subjects import RuntimeSubjectResolver
from app.services.stylist_runtime_settings import StylistRuntimeSettingsService
from app.services.usage_access_policy import UsageAccessPolicyService


class _FakeSettingsRepository:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            daily_generation_limit_non_admin="5",
            daily_chat_seconds_limit_non_admin="600",
            message_cooldown_seconds="45",
            try_other_style_cooldown_seconds="90",
        )
        self.updated_payload: dict[str, int] | None = None

    async def get_or_create_singleton(self, session):
        return self.settings

    async def update(self, session, settings, payload: dict[str, int]):
        self.updated_payload = payload
        for key, value in payload.items():
            setattr(settings, key, value)
        return settings


class _FakeRuntimeSettingsService:
    def __init__(self, limits: StylistRuntimeLimits) -> None:
        self.limits = limits

    async def get_limits(self, session) -> StylistRuntimeLimits:
        return self.limits


class _FakeSubjectSettings:
    secret_key = "test-secret"


class _UsageAccessPolicyForTest(UsageAccessPolicyService):
    def __init__(self, *, generation_usage: int, chat_seconds_usage: int, limits: StylistRuntimeLimits) -> None:
        super().__init__(runtime_settings_service=_FakeRuntimeSettingsService(limits))
        self.generation_usage = generation_usage
        self.chat_seconds_usage = chat_seconds_usage

    async def _count_generation_jobs_today(self, session, *, subject: UserContext) -> int:
        return self.generation_usage

    async def _sum_text_chat_seconds_today(self, session, *, subject: UserContext) -> int:
        return self.chat_seconds_usage


class _ThrottleWithDecisions(InteractionThrottleService):
    def __init__(self, decisions: list[ThrottleDecision]) -> None:
        super().__init__(
            runtime_settings_service=_FakeRuntimeSettingsService(
                StylistRuntimeLimits(
                    daily_generation_limit_non_admin=5,
                    daily_chat_seconds_limit_non_admin=600,
                    message_cooldown_seconds=45,
                    try_other_style_cooldown_seconds=90,
                )
            )
        )
        self.decisions = decisions

    async def _active_blocking_decisions(self, session, *, subject_id: str) -> list[ThrottleDecision]:
        return self.decisions


class StylistRuntimeSettingsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_limits_casts_site_settings_to_runtime_limits(self) -> None:
        repository = _FakeSettingsRepository()
        service = StylistRuntimeSettingsService(repository=repository)

        limits = await service.get_limits(session=object())

        self.assertEqual(limits.daily_generation_limit_non_admin, 5)
        self.assertEqual(limits.daily_chat_seconds_limit_non_admin, 600)
        self.assertEqual(limits.message_cooldown_seconds, 45)
        self.assertEqual(limits.try_other_style_cooldown_seconds, 90)

    async def test_update_delegates_payload_to_repository(self) -> None:
        repository = _FakeSettingsRepository()
        service = StylistRuntimeSettingsService(repository=repository)

        updated = await service.update(session=object(), payload={"message_cooldown_seconds": 30})

        self.assertEqual(repository.updated_payload, {"message_cooldown_seconds": 30})
        self.assertEqual(updated.message_cooldown_seconds, 30)


class UsageAccessPolicyServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_evaluate_denies_generation_when_daily_generation_limit_is_reached(self) -> None:
        service = _UsageAccessPolicyForTest(
            generation_usage=5,
            chat_seconds_usage=120,
            limits=StylistRuntimeLimits(
                daily_generation_limit_non_admin=5,
                daily_chat_seconds_limit_non_admin=600,
                message_cooldown_seconds=45,
                try_other_style_cooldown_seconds=90,
            ),
        )

        decision = await service.evaluate(
            session=object(),
            subject=UserContext(subject_id="session:abc", session_id="abc", is_admin=False),
            action=RequestedAction(action_type="generation"),
        )

        self.assertFalse(decision.is_allowed)
        self.assertEqual(decision.denial_reason, USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT)
        self.assertEqual(decision.remaining_generations, 0)
        self.assertEqual(decision.remaining_chat_seconds, 480)

    async def test_evaluate_denies_text_chat_when_daily_chat_seconds_limit_is_reached(self) -> None:
        service = _UsageAccessPolicyForTest(
            generation_usage=1,
            chat_seconds_usage=600,
            limits=StylistRuntimeLimits(
                daily_generation_limit_non_admin=5,
                daily_chat_seconds_limit_non_admin=600,
                message_cooldown_seconds=45,
                try_other_style_cooldown_seconds=90,
            ),
        )

        decision = await service.evaluate(
            session=object(),
            subject=UserContext(subject_id="session:abc", session_id="abc", is_admin=False),
            action=RequestedAction(action_type="text_chat"),
        )

        self.assertFalse(decision.is_allowed)
        self.assertEqual(decision.denial_reason, USAGE_DENIAL_REASON_DAILY_CHAT_SECONDS_LIMIT)
        self.assertEqual(decision.remaining_generations, 4)
        self.assertEqual(decision.remaining_chat_seconds, 0)

    async def test_evaluate_allows_admin_even_when_usage_exceeds_limits(self) -> None:
        service = _UsageAccessPolicyForTest(
            generation_usage=50,
            chat_seconds_usage=5000,
            limits=StylistRuntimeLimits(
                daily_generation_limit_non_admin=5,
                daily_chat_seconds_limit_non_admin=600,
                message_cooldown_seconds=45,
                try_other_style_cooldown_seconds=90,
            ),
        )

        decision = await service.evaluate(
            session=object(),
            subject=UserContext(subject_id="user:1", session_id="abc", user_id=1, is_admin=True),
            action=RequestedAction(action_type="generation"),
        )

        self.assertTrue(decision.is_allowed)
        self.assertIsNone(decision.denial_reason)
        self.assertEqual(decision.remaining_generations, 0)
        self.assertEqual(decision.remaining_chat_seconds, 0)

    def test_build_subject_requires_session_id_or_server_client_metadata_for_anonymous_subjects(self) -> None:
        service = UsageAccessPolicyService(
            subject_resolver=RuntimeSubjectResolver(settings=_FakeSubjectSettings())
        )

        with self.assertRaises(ValueError):
            service.build_subject(session_id=None, metadata={})

    def test_build_subject_uses_stable_server_client_identity_for_anonymous_subjects(self) -> None:
        service = UsageAccessPolicyService(
            subject_resolver=RuntimeSubjectResolver(settings=_FakeSubjectSettings())
        )

        first = service.build_subject(
            session_id="first-browser-session",
            metadata={},
            request_meta=SimpleNamespace(client_ip="203.0.113.10", client_user_agent="Browser A"),
        )
        second = service.build_subject(
            session_id="after-cache-clear-session",
            metadata={},
            request_meta=SimpleNamespace(client_ip="203.0.113.10", client_user_agent="Browser A"),
        )

        self.assertTrue(first.subject_id.startswith("anonymous:"))
        self.assertEqual(first.subject_id, second.subject_id)
        self.assertEqual(first.session_id, "first-browser-session")
        self.assertEqual(second.session_id, "after-cache-clear-session")


class InteractionThrottleServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_can_submit_allows_when_no_blocking_decisions_exist(self) -> None:
        service = _ThrottleWithDecisions([])

        decision = await service.can_submit(
            session=object(),
            subject_id="session:abc",
            action_type=THROTTLE_ACTION_MESSAGE,
        )

        self.assertTrue(decision.is_allowed)
        self.assertEqual(decision.retry_after_seconds, 0)
        self.assertEqual(decision.cooldown_seconds, 0)

    async def test_can_submit_returns_longest_active_cooldown(self) -> None:
        service = _ThrottleWithDecisions(
            [
                ThrottleDecision(
                    is_allowed=False,
                    action_type=THROTTLE_ACTION_MESSAGE,
                    retry_after_seconds=10,
                    next_allowed_at=None,
                    cooldown_seconds=45,
                ),
                ThrottleDecision(
                    is_allowed=False,
                    action_type=THROTTLE_ACTION_TRY_OTHER_STYLE,
                    retry_after_seconds=25,
                    next_allowed_at=None,
                    cooldown_seconds=90,
                ),
            ]
        )

        decision = await service.can_submit(
            session=object(),
            subject_id="session:abc",
            action_type=THROTTLE_ACTION_MESSAGE,
        )

        self.assertFalse(decision.is_allowed)
        self.assertEqual(decision.action_type, THROTTLE_ACTION_TRY_OTHER_STYLE)
        self.assertEqual(decision.retry_after_seconds, 25)
        self.assertEqual(decision.cooldown_seconds, 90)

    async def test_resolve_cooldown_seconds_uses_action_specific_setting(self) -> None:
        service = InteractionThrottleService(
            runtime_settings_service=_FakeRuntimeSettingsService(
                StylistRuntimeLimits(
                    daily_generation_limit_non_admin=5,
                    daily_chat_seconds_limit_non_admin=600,
                    message_cooldown_seconds=45,
                    try_other_style_cooldown_seconds=90,
                )
            )
        )

        message_cooldown = await service._resolve_cooldown_seconds(
            session=object(),
            action_type=THROTTLE_ACTION_MESSAGE,
        )
        try_other_style_cooldown = await service._resolve_cooldown_seconds(
            session=object(),
            action_type=THROTTLE_ACTION_TRY_OTHER_STYLE,
        )

        self.assertEqual(message_cooldown, 45)
        self.assertEqual(try_other_style_cooldown, 90)


if __name__ == "__main__":
    unittest.main()
