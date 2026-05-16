import unittest
from unittest.mock import patch

from app.infrastructure.comfy.client.comfy_client import ComfyClient
from app.models.enums import GenerationStatus


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *, history, queue):
        self.history = history
        self.queue = queue

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return None

    async def get(self, url):
        if "/history/" in url:
            return FakeResponse(self.history)
        if url.endswith("/queue"):
            return FakeResponse(self.queue)
        raise AssertionError(f"Unexpected URL: {url}")


class ComfyClientStatusTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_prompt_without_output_image_is_failed(self) -> None:
        prompt_id = "prompt-no-image"
        history = {
            prompt_id: {
                "status": {"completed": True},
                "outputs": {},
            }
        }
        queue = {"queue_pending": [], "queue_running": []}
        client = ComfyClient()

        with patch(
            "app.infrastructure.comfy.client.comfy_client.httpx.AsyncClient",
            return_value=FakeAsyncClient(history=history, queue=queue),
        ):
            status = await client.get_job_status(prompt_id)

        self.assertEqual(status.status, GenerationStatus.FAILED)
        self.assertEqual(status.progress, 100)
        self.assertIn("did not return an output image", status.error_message or "")

