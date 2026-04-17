import unittest
from types import SimpleNamespace

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.product_behavior.services.generation_policy_service import GenerationPolicyService
from app.application.product_behavior.services.post_action_conversation_policy import PostActionConversationPolicy
from app.application.product_behavior.services.session_flow_state_service import SessionFlowStateService
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    ConversationRoutingResult,
    GenerationScheduleRequest,
    GenerationScheduleResult,
    KnowledgeItem,
    KnowledgeResult,
    LLMReasonerContextLimitError,
    LLMReasonerError,
    OccasionExtractionOutput,
    ReasoningOutput,
)
from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.handlers.general_advice_handler import GeneralAdviceHandler
from app.application.stylist_chat.handlers.occasion_outfit_handler import OccasionOutfitHandler
from app.application.stylist_chat.handlers.style_exploration_handler import StyleExplorationHandler
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.orchestrator.mode_router import ModeRouter
from app.application.stylist_chat.orchestrator.stylist_chat_orchestrator import StylistChatOrchestrator
from app.application.stylist_chat.results.decision_result import DecisionType
from app.application.stylist_chat.services.candidate_style_selector import CandidateStyleSelector
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.application.stylist_chat.services.occasion_extraction_service import OccasionExtractionService
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.services.routing_context_builder import RoutingContextBuilder
from app.application.stylist_chat.services.semantic_diversity_service import SemanticDiversityService
from app.application.stylist_chat.services.style_exploration_context_builder import StyleExplorationContextBuilder
from app.application.stylist_chat.services.style_history_service import StyleHistoryService
from app.application.stylist_chat.services.visual_diversity_service import VisualDiversityService
from app.application.stylist_chat.use_cases.build_diversity_constraints import BuildDiversityConstraintsUseCase
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.build_occasion_outfit_brief import BuildOccasionOutfitBriefUseCase
from app.application.stylist_chat.use_cases.build_style_exploration_brief import BuildStyleExplorationBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.continue_occasion_outfit import ContinueOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.persist_style_direction import PersistStyleDirectionUseCase
from app.application.stylist_chat.use_cases.select_candidate_style import SelectCandidateStyleUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_occasion_outfit import StartOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.start_style_exploration import StartStyleExplorationUseCase
from app.application.stylist_chat.use_cases.update_occasion_context import UpdateOccasionContextUseCase
from app.domain.chat_context import ChatModeContext, StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy
from app.domain.routing import RoutingDecision, RoutingMode
from app.domain.style_exploration.policies.semantic_diversity_policy import SemanticDiversityPolicy
from app.domain.style_exploration.policies.visual_diversity_policy import VisualDiversityPolicy
from app.infrastructure.knowledge.garment_knowledge_provider import StaticGarmentKnowledgeProvider
from app.infrastructure.knowledge.occasion_knowledge_provider import StaticOccasionKnowledgeProvider
from app.infrastructure.llm.llm_garment_extractor import LLMGarmentExtractorAdapter
from app.models.enums import GenerationStatus
from app.services.chat_mode_resolver import chat_mode_resolver


class FakeContextStore:
    def __init__(self) -> None:
        self.record = object()
        self.context = ChatModeContext()
        self.saved_contexts: list[ChatModeContext] = []

    async def load(self, session_id: str):
        return self.record, self.context.model_copy(deep=True)

    async def save(self, *, session_id: str, context: ChatModeContext, record):
        self.context = context.model_copy(deep=True)
        self.saved_contexts.append(self.context.model_copy(deep=True))
        return self.record


class FakeConversationRouter:
    def __init__(self) -> None:
        self.context_builder = RoutingContextBuilder()

    async def route(self, *, command: ChatCommand, context: ChatModeContext) -> ConversationRoutingResult:
        resolution = chat_mode_resolver.resolve(
            context=context,
            requested_intent=command.requested_intent,
            command_name=command.command_name,
            command_step=command.command_step,
            metadata=command.metadata,
        )
        routing_mode = RoutingMode(resolution.active_mode.value)
        routing_context = self.context_builder.build_context(command=command, context=context)
        routing_input = self.context_builder.build_input(command=command, context=context)
        return ConversationRoutingResult(
            decision=RoutingDecision(
                mode=routing_mode,
                continue_existing_flow=resolution.continue_existing_flow,
                should_reset_to_general=(
                    resolution.active_mode == ChatMode.GENERAL_ADVICE
                    and context.active_mode != ChatMode.GENERAL_ADVICE
                ),
            ),
            routing_input=routing_input,
            routing_context=routing_context,
            provider="fake-router",
        )


class FakeReasoner:
    def __init__(self) -> None:
        self.reply_text = "Mock stylist reply"
        self.image_brief = "cohesive editorial flat lay outfit"
        self.route = "text_only"
        self.raise_error = False
        self.raise_context_limit = False
        self.occasion_output = OccasionExtractionOutput()
        self.last_reasoning_input: dict[str, object] | None = None

    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        self.last_reasoning_input = reasoning_input
        if self.raise_context_limit:
            raise LLMReasonerContextLimitError("context limit")
        if self.raise_error:
            raise LLMReasonerError("provider unavailable")
        return ReasoningOutput(
            reply_text=self.reply_text,
            image_brief_en=self.image_brief,
            route=self.route,
            provider="fake-vllm",
            reasoning_mode="primary",
        )

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        return self.occasion_output


class FakeFallbackReasoner:
    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text="Fallback reply" if locale == "en" else "Fallback reply ru",
            image_brief_en="fallback editorial flat lay outfit",
            route="text_and_generation",
            provider="fake-fallback",
            reasoning_mode="fallback",
        )


class FakeKnowledgeProvider:
    async def fetch(self, *, query: dict[str, object]) -> KnowledgeResult:
        return KnowledgeResult(
            items=[KnowledgeItem("rule", "Keep the outfit coherent."), KnowledgeItem("fit", "Balance proportions.")],
            source="test",
            query=query,
        )


class FakePromptBuilder:
    async def build(self, *, brief: dict[str, object]) -> dict[str, object]:
        style_brief = brief.get("style_exploration_brief") or {}
        mode = str(brief.get("mode") or "general_advice")
        workflow_name = {
            "garment_matching": "garment_matching_variation",
            "occasion_outfit": "occasion_outfit_variation",
            "style_exploration": "style_exploration_variation",
        }.get(mode, "fashion_flatlay_base")
        visual_preset = {
            "garment_matching": "editorial_studio",
            "occasion_outfit": "practical_board",
            "style_exploration": style_brief.get("visual_preset") or "textured_surface",
        }.get(mode, "editorial_studio")
        style_exploration_layouts = {
            "editorial_studio": "centered anchor composition",
            "airy_catalog": "catalog grid-like arrangement",
            "textured_surface": "diagonal editorial spread",
            "dark_gallery": "radial outfit spread",
        }
        style_exploration_backgrounds = {
            "editorial_studio": "muted studio background",
            "airy_catalog": "off-white linen",
            "textured_surface": "warm wood",
            "dark_gallery": "dark textured surface",
        }
        layout_archetype = {
            "garment_matching": "centered anchor composition",
            "occasion_outfit": "practical dressing board",
            "style_exploration": style_exploration_layouts.get(str(visual_preset), "diagonal editorial spread"),
        }.get(mode, "catalog grid-like arrangement")
        background_family = {
            "garment_matching": "muted studio background",
            "occasion_outfit": "neutral paper",
            "style_exploration": style_exploration_backgrounds.get(str(visual_preset), "off-white linen"),
        }.get(mode, "muted studio background")
        shadow_hardness = "soft diffused" if mode == "occasion_outfit" else "moderate natural"
        visual_generation_plan = {
            "mode": mode,
            "style_id": (
                (style_brief.get("selected_style_direction", {}) or {}).get("style_id")
                if isinstance(style_brief, dict)
                else None
            ),
            "style_name": (
                (style_brief.get("selected_style_direction", {}) or {}).get("style_name")
                if isinstance(style_brief, dict)
                else None
            ),
            "final_prompt": f"prompt::{brief.get('image_brief_en', '')}",
            "negative_prompt": "avoid clutter",
            "visual_preset_id": visual_preset,
            "workflow_name": workflow_name,
            "workflow_version": f"{workflow_name}.json",
            "layout_archetype": layout_archetype,
            "background_family": background_family,
            "object_count_range": "balanced outfit set",
            "spacing_density": "balanced",
            "camera_distance": "medium flat lay",
            "shadow_hardness": shadow_hardness,
            "anchor_garment_centrality": "high" if mode == "garment_matching" else "medium",
            "practical_coherence": "high" if mode == "occasion_outfit" else "medium",
            "diversity_profile": dict(brief.get("anti_repeat_constraints") or {}),
        }
        return {
            "prompt": f"prompt::{brief.get('image_brief_en', '')}",
            "image_brief_en": brief.get("image_brief_en", ""),
            "recommendation_text": brief.get("recommendation_text", ""),
            "input_asset_id": brief.get("asset_id"),
            "negative_prompt": "avoid clutter",
            "visual_preset": visual_preset,
            "visual_generation_plan": visual_generation_plan,
            "generation_metadata": {
                "mode": mode,
                "style_id": visual_generation_plan["style_id"],
                "style_name": visual_generation_plan["style_name"],
                "final_prompt": visual_generation_plan["final_prompt"],
                "negative_prompt": "avoid clutter",
                "workflow_name": workflow_name,
                "workflow_version": f"{workflow_name}.json",
                "visual_preset_id": visual_preset,
                "background_family": background_family,
                "layout_archetype": layout_archetype,
                "spacing_density": "balanced",
                "camera_distance": "medium flat lay",
                "shadow_hardness": shadow_hardness,
                "anchor_garment_centrality": visual_generation_plan["anchor_garment_centrality"],
                "practical_coherence": visual_generation_plan["practical_coherence"],
                "diversity_constraints": dict(brief.get("anti_repeat_constraints") or {}),
            },
            "metadata": {
                "style_name": (
                    style_brief.get("selected_style_direction", {}) or {}
                ).get("style_name"),
                "visual_preset": visual_preset,
                "semantic_constraints_hash": style_brief.get("semantic_constraints_hash"),
                "visual_constraints_hash": style_brief.get("visual_constraints_hash"),
                "previous_style_directions": brief.get("previous_style_directions") or [],
                "anti_repeat_constraints": brief.get("anti_repeat_constraints") or {},
                "workflow_name": workflow_name,
                "workflow_version": f"{workflow_name}.json",
                "layout_archetype": layout_archetype,
                "background_family": background_family,
                "object_count_range": "balanced outfit set",
                "spacing_density": "balanced",
                "camera_distance": "medium flat lay",
                "shadow_hardness": shadow_hardness,
                "anchor_garment_centrality": visual_generation_plan["anchor_garment_centrality"],
                "practical_coherence": visual_generation_plan["practical_coherence"],
            },
        }


class FakeStyleHistoryProvider:
    def __init__(self) -> None:
        self.styles = [
            StyleDirectionContext(
                style_id="artful-minimalism",
                style_name="Artful Minimalism",
                style_family="modern minimalism",
                palette=["chalk", "charcoal"],
                silhouette_family="clean and elongated",
                hero_garments=["structured coat"],
                footwear=["sharp leather shoes"],
                accessories=["watch"],
                materials=["wool"],
                styling_mood=["quiet", "precise"],
                composition_type="editorial flat lay",
                background_family="stone",
                layout_density="compact",
                camera_distance="tight overhead",
                visual_preset="editorial_studio",
            ),
            StyleDirectionContext(
                style_id="soft-retro-prep",
                style_name="Soft Retro Prep",
                style_family="soft prep",
                palette=["camel", "cream"],
                silhouette_family="relaxed collegiate layering",
                hero_garments=["oxford shirt"],
                footwear=["loafers"],
                accessories=["belt"],
                materials=["cotton"],
                styling_mood=["polished", "warm"],
                composition_type="editorial flat lay",
                background_family="paper",
                layout_density="balanced",
                camera_distance="medium overhead",
                visual_preset="airy_catalog",
            ),
        ]
        self.index = 0
        self.persisted_history: list[StyleDirectionContext] = []

    async def get_recent(self, session_id: str):
        return [item.model_copy(deep=True) for item in self.persisted_history[-5:]]

    async def pick_next(self, *, session_id: str, style_history: list[StyleDirectionContext]):
        style = self.styles[self.index % len(self.styles)]
        self.index += 1
        return style, None

    async def record_exposure(self, *, session_id: str, style_direction) -> None:
        if self.index > 0:
            self.persisted_history.append(self.styles[(self.index - 1) % len(self.styles)].model_copy(deep=True))
        return None


class FakeGenerationScheduler:
    def __init__(self) -> None:
        self.enqueued: list[GenerationScheduleRequest] = []
        self.block_active = False
        self.fail_next = False
        self.job_statuses: dict[str, GenerationStatus] = {}
        self.session_flow_state_service = SessionFlowStateService()

    async def sync_context(self, context: ChatModeContext) -> ChatModeContext:
        if context.current_job_id and context.current_job_id in self.job_statuses:
            return self.session_flow_state_service.sync_generation_status(
                context=context,
                generation_status=self.job_statuses[context.current_job_id],
            )
        if context.current_job_id and context.flow_state == FlowState.READY_FOR_GENERATION:
            context.flow_state = FlowState.GENERATION_QUEUED
        return context

    async def enqueue(self, request: GenerationScheduleRequest) -> GenerationScheduleResult:
        if self.block_active:
            return GenerationScheduleResult(
                job_id="job-active",
                status=GenerationStatus.RUNNING.value,
                job=SimpleNamespace(id=99, public_id="job-active", status=GenerationStatus.RUNNING),
                blocked_by_active_job=True,
            )
        if self.fail_next:
            self.fail_next = False
            return GenerationScheduleResult(
                job_id=None,
                status=GenerationStatus.FAILED.value,
                job=None,
            )
        self.enqueued.append(request)
        job_id = f"job-{len(self.enqueued)}"
        self.job_statuses[job_id] = GenerationStatus.PENDING
        return GenerationScheduleResult(
            job_id=job_id,
            status=GenerationStatus.PENDING.value,
            job=SimpleNamespace(id=len(self.enqueued), public_id=job_id, status=GenerationStatus.PENDING),
        )


class FakeEventLogger:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    async def emit(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, payload))


class FakeMetricsRecorder:
    def __init__(self) -> None:
        self.counters: list[tuple[str, int, dict[str, object]]] = []
        self.observations: list[tuple[str, float, dict[str, object]]] = []

    async def increment(
        self,
        metric_name: str,
        *,
        value: int = 1,
        tags: dict[str, object] | None = None,
    ) -> None:
        self.counters.append((metric_name, value, tags or {}))

    async def observe(
        self,
        metric_name: str,
        *,
        value: float,
        tags: dict[str, object] | None = None,
    ) -> None:
        self.observations.append((metric_name, value, tags or {}))


class FakeCheckpointWriter:
    def __init__(self) -> None:
        self.saved_contexts: list[ChatModeContext] = []

    async def save_checkpoint(self, *, session_id: str, context: ChatModeContext) -> None:
        self.saved_contexts.append(context.model_copy(deep=True))


def build_test_orchestrator():
    context_store = FakeContextStore()
    conversation_router = FakeConversationRouter()
    reasoner = FakeReasoner()
    fallback_reasoner = FakeFallbackReasoner()
    knowledge_provider = FakeKnowledgeProvider()
    style_history_provider = FakeStyleHistoryProvider()
    generation_scheduler = FakeGenerationScheduler()
    event_logger = FakeEventLogger()
    metrics_recorder = FakeMetricsRecorder()
    checkpoint_writer = FakeCheckpointWriter()

    reasoning_context_builder = ReasoningContextBuilder()
    generation_request_builder = GenerationRequestBuilder(
        prompt_builder=FakePromptBuilder(),
        generation_policy_service=GenerationPolicyService(),
    )
    clarification_builder = ClarificationMessageBuilder()
    diversity_constraints_builder = DiversityConstraintsBuilder()
    garment_matching_context_builder = GarmentMatchingContextBuilder()
    garment_brief_compiler = GarmentBriefCompiler()
    occasion_context_builder = OccasionContextBuilder()
    occasion_brief_compiler = OccasionBriefCompiler()
    style_history_service = StyleHistoryService()
    style_exploration_context_builder = StyleExplorationContextBuilder()
    garment_extractor = LLMGarmentExtractorAdapter()
    occasion_extractor = OccasionExtractionService(reasoner=reasoner)
    garment_completeness_policy = GarmentCompletenessPolicy()
    garment_clarification_policy = GarmentClarificationPolicy()
    garment_clarification_service = GarmentClarificationService(garment_clarification_policy)
    occasion_completeness_policy = OccasionCompletenessPolicy()
    occasion_clarification_policy = OccasionClarificationPolicy()
    occasion_clarification_service = OccasionClarificationService(occasion_clarification_policy)
    garment_knowledge_provider = StaticGarmentKnowledgeProvider()
    occasion_knowledge_provider = StaticOccasionKnowledgeProvider()
    candidate_style_selector = CandidateStyleSelector(style_history_provider)
    semantic_diversity_service = SemanticDiversityService(SemanticDiversityPolicy())
    visual_diversity_service = VisualDiversityService(VisualDiversityPolicy())
    start_garment_matching = StartGarmentMatchingUseCase(clarification_builder)
    start_occasion_outfit = StartOccasionOutfitUseCase(clarification_builder)
    start_style_exploration = StartStyleExplorationUseCase()
    continue_garment_matching = ContinueGarmentMatchingUseCase(
        garment_extractor=garment_extractor,
        garment_completeness_evaluator=garment_completeness_policy,
        garment_clarification_service=garment_clarification_service,
    )
    continue_occasion_outfit = ContinueOccasionOutfitUseCase(
        occasion_context_extractor=occasion_extractor,
        update_occasion_context=UpdateOccasionContextUseCase(
            completeness_evaluator=occasion_completeness_policy,
        ),
        occasion_clarification_service=occasion_clarification_service,
    )
    build_garment_outfit_brief = BuildGarmentOutfitBriefUseCase(
        garment_knowledge_provider=garment_knowledge_provider,
        garment_matching_context_builder=garment_matching_context_builder,
        outfit_brief_builder=garment_brief_compiler,
        garment_brief_compiler=garment_brief_compiler,
    )
    build_occasion_outfit_brief = BuildOccasionOutfitBriefUseCase(
        occasion_knowledge_provider=occasion_knowledge_provider,
        occasion_context_builder=occasion_context_builder,
        outfit_brief_builder=occasion_brief_compiler,
        occasion_brief_compiler=occasion_brief_compiler,
    )
    select_candidate_style = SelectCandidateStyleUseCase(
        candidate_selector=candidate_style_selector,
        style_history_provider=style_history_provider,
        style_history_service=style_history_service,
    )
    build_diversity_constraints = BuildDiversityConstraintsUseCase(
        semantic_diversity_builder=semantic_diversity_service,
        visual_diversity_builder=visual_diversity_service,
    )
    build_style_exploration_brief = BuildStyleExplorationBriefUseCase(
        context_builder=style_exploration_context_builder,
    )
    persist_style_direction = PersistStyleDirectionUseCase(
        style_history_service=style_history_service,
    )
    conversation_state_policy = ConversationStatePolicy()
    post_action_conversation_policy = PostActionConversationPolicy()
    shared_kwargs = {
        "reasoner": reasoner,
        "fallback_reasoner": fallback_reasoner,
        "knowledge_provider": knowledge_provider,
        "reasoning_context_builder": reasoning_context_builder,
        "generation_request_builder": generation_request_builder,
    }
    handlers = {
        ChatMode.GENERAL_ADVICE: GeneralAdviceHandler(**shared_kwargs),
        ChatMode.GARMENT_MATCHING: GarmentMatchingHandler(
            start_use_case=start_garment_matching,
            continue_use_case=continue_garment_matching,
            build_outfit_brief_use_case=build_garment_outfit_brief,
            **shared_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            start_use_case=start_occasion_outfit,
            continue_use_case=continue_occasion_outfit,
            build_outfit_brief_use_case=build_occasion_outfit_brief,
            context_checkpoint_writer=checkpoint_writer,
            **shared_kwargs,
        ),
        ChatMode.STYLE_EXPLORATION: StyleExplorationHandler(
            start_use_case=start_style_exploration,
            select_candidate_style_use_case=select_candidate_style,
            build_diversity_constraints_use_case=build_diversity_constraints,
            build_style_exploration_brief_use_case=build_style_exploration_brief,
            persist_style_direction_use_case=persist_style_direction,
            style_history_service=style_history_service,
            style_history_provider=style_history_provider,
            context_checkpoint_writer=checkpoint_writer,
            **shared_kwargs,
        ),
    }
    orchestrator = StylistChatOrchestrator(
        context_store=context_store,
        generation_scheduler=generation_scheduler,
        event_logger=event_logger,
        metrics_recorder=metrics_recorder,
        command_dispatcher=CommandDispatcher(
            conversation_router=conversation_router,
            conversation_state_policy=conversation_state_policy,
        ),
        mode_router=ModeRouter(handlers=handlers),
        generation_request_builder=generation_request_builder,
        post_action_conversation_policy=post_action_conversation_policy,
    )
    return (
        orchestrator,
        context_store,
        reasoner,
        generation_scheduler,
        event_logger,
        metrics_recorder,
        checkpoint_writer,
    )


class StylistOrchestratorScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            self.event_logger,
            self.metrics_recorder,
            self.checkpoint_writer,
        ) = build_test_orchestrator()

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    async def test_general_advice_defaults_to_text_only(self) -> None:
        self.reasoner.route = "text_only"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-general-default-1",
                locale="en",
                message="Hi there",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertFalse(response.can_offer_visualization)
        self.assertIsNone(response.job_id)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.COMPLETED)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_general_advice_text_and_generation_route_offers_cta_instead_of_auto_generation(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-general-cta-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(response.can_offer_visualization)
        self.assertEqual(response.cta_text, "Build a flat lay reference?")
        self.assertEqual(response.visualization_type, "flat_lay_reference")
        self.assertIsNone(response.job_id)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_explicit_visual_request_generates_from_general_advice(self) -> None:
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-explicit-visual-1",
                locale="ru",
                message="Покажи мягкий интеллектуальный образ на выставку",
                user_message_id=1,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertFalse(response.can_offer_visualization)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_garment_flow_requires_cta_before_generation(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage1-garment-flow-1",
                locale="en",
                message="Style around a garment",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-garment-flow-1",
                locale="en",
                message="black leather jacket",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(response.can_offer_visualization)
        self.assertEqual(response.cta_text, "Build a flat lay around this garment?")
        self.assertIsNone(response.job_id)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GARMENT_MATCHING)
        self.assertEqual(self.context_store.context.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_occasion_flow_requires_cta_before_generation(self) -> None:
        self.reasoner.occasion_output = OccasionExtractionOutput()
        await self.run_command(
            ChatCommand(
                session_id="stage1-occasion-flow-1",
                locale="en",
                message="Need an outfit for an event",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
            )
        )
        self.reasoner.route = "text_and_generation"
        self.reasoner.occasion_output = OccasionExtractionOutput(
            event_type="wedding",
            time_of_day="evening",
            season_or_weather="spring",
            desired_impression="elegant",
        )

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-occasion-flow-1",
                locale="en",
                message="Spring evening wedding, elegant",
                user_message_id=2,
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_ONLY)
        self.assertTrue(response.can_offer_visualization)
        self.assertEqual(response.cta_text, "Build a flat lay for this occasion?")
        self.assertIsNone(response.job_id)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.OCCASION_OUTFIT)
        self.assertEqual(self.context_store.context.flow_state, FlowState.READY_FOR_GENERATION)
        self.assertEqual(len(self.scheduler.enqueued), 0)

    async def test_visualization_cta_confirmation_generates_and_clears_offer(self) -> None:
        self.reasoner.route = "text_and_generation"
        await self.run_command(
            ChatCommand(
                session_id="stage1-cta-confirm-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
            )
        )

        response = await self.run_command(
            ChatCommand(
                session_id="stage1-cta-confirm-1",
                locale="en",
                message="Confirm the visualization",
                user_message_id=2,
                metadata={"source": "visualization_cta", "visualization_type": "flat_lay_reference"},
            )
        )

        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertFalse(response.can_offer_visualization)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
        self.assertIsNone(self.context_store.context.visualization_offer)
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_style_exploration_quick_action_generates_and_completed_job_resets_to_general(self) -> None:
        self.reasoner.route = "text_and_generation"
        generated = await self.run_command(
            ChatCommand(
                session_id="stage1-style-reset-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                metadata={"source": "quick_action"},
            )
        )

        self.assertEqual(generated.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(generated.job_id, "job-1")
        self.assertEqual(self.context_store.context.active_mode, ChatMode.STYLE_EXPLORATION)
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)

        self.scheduler.job_statuses["job-1"] = GenerationStatus.COMPLETED
        self.reasoner.route = "text_only"
        followup = await self.run_command(
            ChatCommand(
                session_id="stage1-style-reset-1",
                locale="en",
                message="Hi there",
                user_message_id=2,
            )
        )

        self.assertEqual(followup.decision_type, DecisionType.TEXT_ONLY)
        self.assertEqual(self.context_store.context.active_mode, ChatMode.GENERAL_ADVICE)
        self.assertEqual(self.context_store.context.flow_state, FlowState.COMPLETED)
        self.assertEqual(len(self.scheduler.enqueued), 1)

    async def test_event_payload_keeps_cta_contract_and_identifiers(self) -> None:
        self.reasoner.route = "text_and_generation"
        response = await self.run_command(
            ChatCommand(
                session_id="stage1-telemetry-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=1,
                client_message_id="client-1",
                command_id="command-1",
                correlation_id="corr-1",
            )
        )

        self.assertEqual(response.context_patch["can_offer_visualization"], True)
        self.assertEqual(response.context_patch["cta_text"], "Build a flat lay reference?")
        self.assertEqual(response.context_patch["visualization_type"], "flat_lay_reference")
        self.assertTrue(self.event_logger.events)
        _, payload = self.event_logger.events[-1]
        self.assertEqual(payload["client_message_id"], "client-1")
        self.assertEqual(payload["command_id"], "command-1")
        self.assertEqual(payload["correlation_id"], "corr-1")
        self.assertEqual(payload["active_mode"], "general_advice")

    async def test_router_event_is_logged_with_debuggable_routing_payload(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage1-routing-log-1",
                locale="en",
                message="How can I modernize a white shirt?",
                user_message_id=7,
                client_message_id="route-client-7",
                command_id="route-command-7",
                correlation_id="route-corr-7",
            )
        )

        routed_events = [event for event in self.event_logger.events if event[0] == "stylist_chat_routed"]
        self.assertTrue(routed_events)
        _, routed_payload = routed_events[-1]
        self.assertEqual(routed_payload["client_message_id"], "route-client-7")
        self.assertEqual(routed_payload["command_id"], "route-command-7")
        self.assertEqual(routed_payload["correlation_id"], "route-corr-7")
        self.assertEqual(routed_payload["provider"], "fake-router")
        self.assertEqual(routed_payload["routing_mode"], "general_advice")
        self.assertIn("routing_input", routed_payload)
        self.assertIn("routing_context", routed_payload)
        self.assertIn("normalized_payload", routed_payload)
        self.assertIn("raw_content_length", routed_payload)
        self.assertIn("recent_messages_count", routed_payload["routing_input"])
        self.assertIn("recent_messages_count", routed_payload["routing_context"])

        orchestrated_events = [event for event in self.event_logger.events if event[0] == "stylist_chat_orchestrated"]
        self.assertTrue(orchestrated_events)
        _, orchestrated_payload = orchestrated_events[-1]
        self.assertEqual(orchestrated_payload["routing_provider"], "fake-router")
        self.assertEqual(orchestrated_payload["routing_mode"], "general_advice")
        self.assertEqual(orchestrated_payload["routing_used_fallback"], False)
