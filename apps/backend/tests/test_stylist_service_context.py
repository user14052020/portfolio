import unittest
from unittest.mock import AsyncMock, patch

from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState

try:
    from app.services.stylist_conversational import StylistService
except ModuleNotFoundError:
    StylistService = None


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
