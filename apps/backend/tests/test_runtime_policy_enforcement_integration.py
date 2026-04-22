from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from fastapi import HTTPException, status

from app.api.routes import generation_jobs as generation_jobs_route
from app.api.routes import stylist_runtime_settings as runtime_settings_route
from app.domain.chat_context import ChatModeContext
from app.domain.interaction_throttle import THROTTLE_ACTION_MESSAGE, ThrottleDecision
from app.domain.usage_access_policy import (
    USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
    RequestedAction,
    UsageDecision,
    UserContext,
)
from app.schemas.generation_job import GenerationJobCreate
from app.schemas.stylist import StylistMessageRequest
from app.schemas.stylist_runtime_settings import StylistRuntimeSettingsUpdate
from app.services import stylist_conversational as stylist_module
from app.services.stylist_conversational import StylistService


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class _DenyingGenerationPolicy:
    def __init__(self) -> None:
        self.requested_action: RequestedAction | None = None
        self.subject = UserContext(
            subject_id="session:quota-session",
            session_id="quota-session",
            is_admin=False,
        )

    def build_subject(self, *, current_user, session_id, metadata, request_meta=None) -> UserContext:
        return self.subject

    async def evaluate(self, session, *, subject: UserContext, action: RequestedAction) -> UsageDecision:
        self.requested_action = action
        return UsageDecision(
            is_allowed=False,
            denial_reason=USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT,
            remaining_generations=0,
            remaining_chat_seconds=120,
        )


class _RecordingRuntimePolicyObservability:
    def __init__(self) -> None:
        self.usage_records: list[dict] = []
        self.cooldown_records: list[dict] = []

    async def record_usage_access_decision(self, **payload) -> None:
        self.usage_records.append(payload)

    async def record_cooldown_decision(self, **payload) -> None:
        self.cooldown_records.append(payload)


class _AllowingUsagePolicy:
    def __init__(self) -> None:
        self.subject = UserContext(
            subject_id="session:cooldown-session",
            session_id="cooldown-session",
            is_admin=False,
        )

    def build_subject(self, *, current_user, session_id, metadata, request_meta=None) -> UserContext:
        return self.subject

    async def evaluate(self, session, *, subject: UserContext, action: RequestedAction) -> UsageDecision:
        return UsageDecision(
            is_allowed=True,
            denial_reason=None,
            remaining_generations=5,
            remaining_chat_seconds=600,
        )


class _DenyingThrottle:
    def __init__(self, decision: ThrottleDecision) -> None:
        self.decision = decision
        self.subject_id: str | None = None
        self.action_type: str | None = None

    async def can_submit(self, session, *, subject_id: str, action_type: str) -> ThrottleDecision:
        self.subject_id = subject_id
        self.action_type = action_type
        return self.decision


class _FakeChatContextStore:
    async def load(self, session, session_id: str):
        return None, ChatModeContext()


class _NoWriteChatMessagesRepository:
    def __init__(self) -> None:
        self.create_called = False

    async def list_by_session(self, session, session_id: str, *, limit: int, created_at_from=None):
        return []

    async def create(self, session, payload: dict):
        self.create_called = True
        raise AssertionError("Cooldown denial must happen before message persistence.")


class _PolicyOnlyStylistService(StylistService):
    async def _sync_context_generation_state(self, session, context: ChatModeContext) -> ChatModeContext:
        return context

    async def _resolve_context_asset(self, *, session, payload, recent_messages, context):
        return None


class _RuntimeSettingsRouteService:
    def __init__(self) -> None:
        self.updated_payload: dict | None = None
        self.settings = SimpleNamespace(
            id=1,
            daily_generation_limit_non_admin=3,
            daily_chat_seconds_limit_non_admin=300,
            message_cooldown_seconds=15,
            try_other_style_cooldown_seconds=45,
            created_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
        )

    async def update(self, session, *, payload: dict):
        self.updated_payload = payload
        for key, value in payload.items():
            setattr(self.settings, key, value)
        return self.settings


class RuntimePolicyEnforcementIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_generation_api_enforces_non_admin_quota(self) -> None:
        original_policy = generation_jobs_route.usage_access_policy_service
        original_observability = generation_jobs_route.runtime_policy_observability
        fake_policy = _DenyingGenerationPolicy()
        fake_observability = _RecordingRuntimePolicyObservability()
        session = _FakeSession()
        payload = GenerationJobCreate(
            session_id="quota-session",
            recommendation_ru="RU",
            recommendation_en="EN",
            prompt="render a concise outfit",
        )

        generation_jobs_route.usage_access_policy_service = fake_policy
        generation_jobs_route.runtime_policy_observability = fake_observability
        try:
            with self.assertRaises(HTTPException) as raised:
                await generation_jobs_route.create_generation_job(payload, session=session, current_user=None)
        finally:
            generation_jobs_route.usage_access_policy_service = original_policy
            generation_jobs_route.runtime_policy_observability = original_observability

        self.assertEqual(raised.exception.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(raised.exception.detail["code"], USAGE_DENIAL_REASON_DAILY_GENERATION_LIMIT)
        self.assertEqual(raised.exception.detail["remaining_generations"], 0)
        self.assertEqual(raised.exception.detail["remaining_chat_seconds"], 120)
        self.assertEqual(fake_policy.requested_action, RequestedAction(action_type="generation"))
        self.assertEqual(fake_observability.usage_records[0]["surface"], "generation_jobs_api")
        self.assertEqual(session.commit_count, 0)

    async def test_stylist_message_enforces_cooldown_before_persistence(self) -> None:
        original_context_store = stylist_module.chat_context_store
        original_messages_repository = stylist_module.chat_messages_repository
        fake_messages_repository = _NoWriteChatMessagesRepository()
        next_allowed_at = datetime(2026, 4, 13, 8, 30, tzinfo=timezone.utc)
        fake_observability = _RecordingRuntimePolicyObservability()
        fake_throttle = _DenyingThrottle(
            ThrottleDecision(
                is_allowed=False,
                action_type=THROTTLE_ACTION_MESSAGE,
                retry_after_seconds=17,
                next_allowed_at=next_allowed_at,
                cooldown_seconds=45,
            )
        )
        service = _PolicyOnlyStylistService()
        service.usage_access_policy_service = _AllowingUsagePolicy()
        service.interaction_throttle_service = fake_throttle
        service.runtime_policy_observability = fake_observability
        payload = StylistMessageRequest(
            session_id="cooldown-session",
            locale="en",
            message="Can I send another message?",
        )

        stylist_module.chat_context_store = _FakeChatContextStore()
        stylist_module.chat_messages_repository = fake_messages_repository
        try:
            with self.assertRaises(HTTPException) as raised:
                await service.process_message(session=_FakeSession(), payload=payload, current_user=None)
        finally:
            stylist_module.chat_context_store = original_context_store
            stylist_module.chat_messages_repository = original_messages_repository

        self.assertEqual(raised.exception.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(raised.exception.detail["code"], "message_cooldown")
        self.assertEqual(raised.exception.detail["retry_after_seconds"], 17)
        self.assertEqual(raised.exception.detail["next_allowed_at"], next_allowed_at.isoformat())
        self.assertEqual(raised.exception.detail["cooldown_seconds"], 45)
        self.assertEqual(raised.exception.detail["action_type"], THROTTLE_ACTION_MESSAGE)
        self.assertEqual(fake_throttle.subject_id, "session:cooldown-session")
        self.assertEqual(fake_throttle.action_type, THROTTLE_ACTION_MESSAGE)
        self.assertEqual(fake_observability.usage_records[0]["surface"], "stylist_message")
        self.assertEqual(fake_observability.cooldown_records[0]["surface"], "stylist_message")
        self.assertFalse(fake_messages_repository.create_called)

    async def test_admin_settings_update_applies_runtime_limits(self) -> None:
        original_service = runtime_settings_route.runtime_settings_service
        fake_service = _RuntimeSettingsRouteService()
        session = _FakeSession()
        payload = StylistRuntimeSettingsUpdate(
            daily_generation_limit_non_admin=7,
            daily_chat_seconds_limit_non_admin=900,
            message_cooldown_seconds=12,
            try_other_style_cooldown_seconds=60,
        )

        runtime_settings_route.runtime_settings_service = fake_service
        try:
            updated = await runtime_settings_route.update_stylist_runtime_settings(
                payload=payload,
                _=SimpleNamespace(id=1),
                session=session,
            )
        finally:
            runtime_settings_route.runtime_settings_service = original_service

        self.assertEqual(fake_service.updated_payload, payload.model_dump())
        self.assertEqual(updated.daily_generation_limit_non_admin, 7)
        self.assertEqual(updated.daily_chat_seconds_limit_non_admin, 900)
        self.assertEqual(updated.message_cooldown_seconds, 12)
        self.assertEqual(updated.try_other_style_cooldown_seconds, 60)
        self.assertEqual(session.commit_count, 1)


if __name__ == "__main__":
    unittest.main()
