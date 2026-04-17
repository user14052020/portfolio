import unittest
import importlib
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from app.models.enums import GenerationProvider
from app.schemas.generation_job import GenerationJobCreate


class GenerationServiceVisualPipelineTests(unittest.TestCase):
    def test_initial_provider_payload_keeps_structured_visual_plan_before_submit(self) -> None:
        fake_redis_asyncio = ModuleType("redis.asyncio")
        fake_redis_asyncio.from_url = lambda *args, **kwargs: SimpleNamespace()
        fake_redis = ModuleType("redis")
        fake_redis.asyncio = fake_redis_asyncio
        sys.modules.pop("app.services.generation", None)
        with patch.dict(sys.modules, {"redis": fake_redis, "redis.asyncio": fake_redis_asyncio}):
            GenerationService = importlib.import_module("app.services.generation").GenerationService
        service = GenerationService(
            settings=SimpleNamespace(redis_url="redis://unused"),
            comfy_client=SimpleNamespace(),
            generation_backend_adapter=SimpleNamespace(),
            redis_client=SimpleNamespace(),
        )
        payload = GenerationJobCreate(
            session_id="stage9-job-1",
            input_text="Build a soft prep outfit",
            recommendation_ru="Собери мягкий prep-образ",
            recommendation_en="Build a soft prep outfit",
            prompt="soft prep editorial flat lay",
            negative_prompt="avoid clutter",
            workflow_name="style_exploration_variation",
            workflow_version="style_exploration_variation.json",
            visual_generation_plan={
                "mode": "style_exploration",
                "final_prompt": "soft prep editorial flat lay",
                "negative_prompt": "avoid clutter",
                "visual_preset_id": "airy_catalog",
                "workflow_name": "style_exploration_variation",
                "workflow_version": "style_exploration_variation.json",
            },
            generation_metadata={
                "mode": "style_exploration",
                "final_prompt": "soft prep editorial flat lay",
                "negative_prompt": "avoid clutter",
                "workflow_name": "style_exploration_variation",
                "workflow_version": "style_exploration_variation.json",
                "visual_preset_id": "airy_catalog",
            },
            metadata={"source_message_id": 41, "visual_preset": "airy_catalog"},
            idempotency_key="stage9-job-1:key",
            provider=GenerationProvider.COMFYUI,
        )

        provider_payload = service._build_initial_provider_payload(payload)

        self.assertEqual(provider_payload["_visual_generation_plan"]["workflow_name"], "style_exploration_variation")
        self.assertEqual(provider_payload["_generation_metadata"]["visual_preset_id"], "airy_catalog")
        self.assertEqual(provider_payload["_stylist"]["negative_prompt"], "avoid clutter")
        self.assertEqual(provider_payload["_stylist"]["source_message_id"], 41)
        self.assertEqual(provider_payload["_orchestration"]["idempotency_key"], "stage9-job-1:key")

    def test_build_style_explanation_prefers_persisted_generation_metadata(self) -> None:
        fake_redis_asyncio = ModuleType("redis.asyncio")
        fake_redis_asyncio.from_url = lambda *args, **kwargs: SimpleNamespace()
        fake_redis = ModuleType("redis")
        fake_redis.asyncio = fake_redis_asyncio
        sys.modules.pop("app.services.generation", None)
        with patch.dict(sys.modules, {"redis": fake_redis, "redis.asyncio": fake_redis_asyncio}):
            GenerationService = importlib.import_module("app.services.generation").GenerationService
        service = GenerationService(
            settings=SimpleNamespace(redis_url="redis://unused"),
            comfy_client=SimpleNamespace(),
            generation_backend_adapter=SimpleNamespace(),
            redis_client=SimpleNamespace(),
        )
        job = SimpleNamespace(
            provider_payload={
                "_generation_metadata": {
                    "style_id": "soft-retro-prep",
                    "style_name": "Soft Retro Prep",
                    "style_explanation_short": "Soft Retro Prep softens classic collegiate codes.",
                    "style_explanation_supporting_text": "It keeps prep recognizable but warmer and less rigid.",
                    "style_explanation_distinct_points": ["warmer palette", "gentler structure"],
                }
            }
        )

        explanation = service._build_style_explanation(job)

        self.assertIsNotNone(explanation)
        self.assertEqual(explanation.style_id, "soft-retro-prep")
        self.assertEqual(explanation.style_name, "Soft Retro Prep")
        self.assertEqual(explanation.short_explanation, "Soft Retro Prep softens classic collegiate codes.")
        self.assertEqual(
            explanation.supporting_text,
            "It keeps prep recognizable but warmer and less rigid.",
        )
        self.assertEqual(explanation.distinct_points, ["warmer palette", "gentler structure"])
