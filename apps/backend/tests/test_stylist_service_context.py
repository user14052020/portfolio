import unittest
from unittest.mock import AsyncMock, patch

from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState

try:
    from app.services.stylist_conversational import StylistService
    from app.services.profile_session_state import ProfileSessionState
except ModuleNotFoundError:
    StylistService = None
    ProfileSessionState = None


@unittest.skipIf(StylistService is None, "fastapi dependency is not available in this test environment")
class StylistServiceContextTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_context_syncs_active_generation_flow_state(self) -> None:
        assert StylistService is not None
        service = StylistService()
        context = ChatModeContext(
            current_job_id="job-public-id",
            flow_state=FlowState.READY_FOR_GENERATION,
        )
        load_mock = AsyncMock(return_value=(None, context))
        scheduler = AsyncMock()
        scheduler.sync_context = AsyncMock(
            return_value=ChatModeContext(
                current_job_id="job-public-id",
                flow_state=FlowState.GENERATION_QUEUED,
            )
        )
        orchestrator = type("OrchestratorStub", (), {"generation_scheduler": scheduler})()

        with patch("app.services.stylist_conversational.chat_context_store.load", load_mock), patch(
            "app.services.stylist_conversational.build_stylist_chat_orchestrator",
            return_value=orchestrator,
        ):
            result = await service.get_context(session=None, session_id="session-123")

        self.assertEqual(result.current_job_id, "job-public-id")
        self.assertEqual(result.flow_state, FlowState.GENERATION_QUEUED)
        load_mock.assert_awaited_once_with(None, "session-123")
        scheduler.sync_context.assert_awaited_once()

    async def test_apply_profile_session_state_uses_profile_layer_completeness_without_reasoning_telemetry(self) -> None:
        assert StylistService is not None
        assert ProfileSessionState is not None
        service = StylistService()
        context = ChatModeContext()

        service._apply_profile_session_state(
            context=context,
            profile_session_state=ProfileSessionState(
                session_profile_context={"presentation_profile": "androgynous"},
                profile_context_snapshot={
                    "present": True,
                    "source": "profile_context_service",
                    "values": {"presentation_profile": "androgynous"},
                },
                profile_recent_updates={"preferred_items": ["blazer"]},
                profile_completeness_state="partial",
            ),
            decision_telemetry={},
        )

        self.assertEqual(context.session_profile_context, {"presentation_profile": "androgynous"})
        self.assertEqual(context.profile_recent_updates, {"preferred_items": ["blazer"]})
        self.assertEqual(context.profile_completeness_state, "partial")

    async def test_apply_profile_session_state_prefers_reasoning_completeness_when_available(self) -> None:
        assert StylistService is not None
        assert ProfileSessionState is not None
        service = StylistService()
        context = ChatModeContext()

        service._apply_profile_session_state(
            context=context,
            profile_session_state=ProfileSessionState(
                session_profile_context={"presentation_profile": "androgynous"},
                profile_context_snapshot={
                    "present": True,
                    "source": "profile_context_service",
                    "values": {"presentation_profile": "androgynous"},
                },
                profile_recent_updates={},
                profile_completeness_state="partial",
            ),
            decision_telemetry={"reasoning_profile_completeness_state": "strong"},
        )

        self.assertEqual(context.profile_completeness_state, "strong")
