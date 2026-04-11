import unittest
from types import SimpleNamespace

from app.application.visual_generation.contracts import PreparedGenerationRun
from app.application.visual_generation.services.comfy_generation_orchestrator import (
    ComfyGenerationOrchestrator,
)
from app.application.visual_generation.services.generation_metadata_recorder import GenerationMetadataRecorder
from app.application.visual_generation.use_cases.persist_generation_result import PersistGenerationResultUseCase
from app.application.visual_generation.use_cases.run_generation_job import RunGenerationJobUseCase
from app.domain.visual_generation import GenerationMetadata, VisualGenerationPlan


class FakeGenerationBackendAdapter:
    def __init__(self) -> None:
        self.received_plan = None

    async def prepare_run(
        self,
        *,
        plan: VisualGenerationPlan,
        input_image_url: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
    ) -> PreparedGenerationRun:
        self.received_plan = plan
        return PreparedGenerationRun(
            workflow_payload={"prompt": {"text": plan.final_prompt}},
            seed=4242,
            workflow_name=plan.workflow_name,
            workflow_version=plan.workflow_version,
        )

    async def submit(self, *, workflow_payload: dict) -> str:
        return "unused"


class FakeMetadataStore:
    def __init__(self) -> None:
        self.saved = None

    async def save_for_job(self, *, job, plan, metadata):
        self.saved = (job, plan, metadata)
        return job


class ComfyGenerationOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_generation_passes_structured_plan_and_persists_trace(self) -> None:
        backend_adapter = FakeGenerationBackendAdapter()
        metadata_store = FakeMetadataStore()
        orchestrator = ComfyGenerationOrchestrator(
            run_generation_job=RunGenerationJobUseCase(generation_backend_adapter=backend_adapter),
            persist_generation_result=PersistGenerationResultUseCase(
                generation_metadata_recorder=GenerationMetadataRecorder(store=metadata_store)
            ),
        )
        job = SimpleNamespace(public_id="job-stage9-1")
        plan = VisualGenerationPlan(
            mode="garment_matching",
            style_id="black-leather-jacket",
            style_name="Black Leather Jacket",
            final_prompt="anchor-led outfit flat lay",
            negative_prompt="avoid clutter",
            visual_preset_id="editorial_studio",
            workflow_name="garment_matching_variation",
            workflow_version="garment_matching_variation.json",
            anchor_garment_centrality="high",
        )
        metadata = GenerationMetadata(
            mode="garment_matching",
            style_id="black-leather-jacket",
            style_name="Black Leather Jacket",
            final_prompt="anchor-led outfit flat lay",
            negative_prompt="avoid clutter",
            workflow_name="garment_matching_variation",
            workflow_version="garment_matching_variation.json",
            visual_preset_id="editorial_studio",
            anchor_garment_centrality="high",
        )

        result = await orchestrator.prepare_generation(
            job=job,
            plan=plan,
            metadata=metadata,
            input_image_url="https://example.com/anchor.jpg",
            body_height_cm=182,
            body_weight_kg=76,
        )

        self.assertEqual(backend_adapter.received_plan.anchor_garment_centrality, "high")
        self.assertEqual(result.plan.workflow_name, "garment_matching_variation")
        self.assertEqual(result.metadata.seed, 4242)
        self.assertEqual(result.metadata.generation_job_id, "job-stage9-1")
        self.assertIs(metadata_store.saved[0], job)
        self.assertEqual(metadata_store.saved[1].visual_preset_id, "editorial_studio")
        self.assertEqual(metadata_store.saved[2].workflow_version, "garment_matching_variation.json")
