import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import FlowState
from app.models.enums import GenerationStatus

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
        get_job_mock = AsyncMock(return_value=SimpleNamespace(status=GenerationStatus.PENDING))

        with patch("app.services.stylist_conversational.chat_context_store.load", load_mock), patch(
            "app.services.stylist_conversational.generation_jobs_repository.get_by_public_id",
            get_job_mock,
        ):
            result = await service.get_context(session=None, session_id="session-123")

        self.assertEqual(result.current_job_id, "job-public-id")
        self.assertEqual(result.flow_state, FlowState.GENERATION_QUEUED)
        load_mock.assert_awaited_once_with(None, "session-123")
        get_job_mock.assert_awaited_once_with(None, "job-public-id")
