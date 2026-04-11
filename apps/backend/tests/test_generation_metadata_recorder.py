import unittest

from app.application.visual_generation.services.generation_metadata_recorder import GenerationMetadataRecorder
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class FakeMetadataStore:
    def __init__(self) -> None:
        self.saved = None

    async def save_for_job(self, *, job, plan, metadata):
        self.saved = (job, plan, metadata)
        return job


class GenerationMetadataRecorderTests(unittest.IsolatedAsyncioTestCase):
    async def test_recorder_persists_plan_and_metadata_through_store(self) -> None:
        store = FakeMetadataStore()
        recorder = GenerationMetadataRecorder(store=store)
        job = object()
        plan = VisualGenerationPlan(
            mode="garment_matching",
            final_prompt="anchor-led outfit",
            negative_prompt="avoid clutter",
            workflow_name="garment_matching_variation",
        )
        metadata = GenerationMetadata(
            mode="garment_matching",
            final_prompt="anchor-led outfit",
            negative_prompt="avoid clutter",
            workflow_name="garment_matching_variation",
        )

        await recorder.record_for_job(job=job, plan=plan, metadata=metadata)

        self.assertIs(store.saved[0], job)
        self.assertEqual(store.saved[1].workflow_name, "garment_matching_variation")
        self.assertEqual(store.saved[2].mode, "garment_matching")
