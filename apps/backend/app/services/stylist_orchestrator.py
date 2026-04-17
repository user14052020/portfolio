from sqlalchemy.ext.asyncio import AsyncSession

from app.application.product_behavior.services.conversation_state_policy import ConversationStatePolicy
from app.application.product_behavior.services.generation_policy_service import GenerationPolicyService
from app.application.product_behavior.services.post_action_conversation_policy import PostActionConversationPolicy
from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.application.knowledge.services.knowledge_retrieval_service import DefaultKnowledgeRetrievalService
from app.application.knowledge.use_cases.build_knowledge_query import BuildKnowledgeQueryUseCase
from app.application.knowledge.use_cases.inject_knowledge_into_reasoning import InjectKnowledgeIntoReasoningUseCase
from app.application.knowledge.use_cases.resolve_knowledge_bundle import ResolveKnowledgeBundleUseCase
from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.handlers.general_advice_handler import GeneralAdviceHandler
from app.application.stylist_chat.handlers.occasion_outfit_handler import OccasionOutfitHandler
from app.application.stylist_chat.handlers.style_exploration_handler import StyleExplorationHandler
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.orchestrator.mode_router import ModeRouter
from app.application.stylist_chat.orchestrator.stylist_chat_orchestrator import StylistChatOrchestrator
from app.application.stylist_chat.services.candidate_style_selector import CandidateStyleSelector
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.conversation_router import ConversationRouter
from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.application.stylist_chat.services.fallback_router_policy import FallbackRouterPolicy
from app.application.stylist_chat.services.fallback_reasoner import DeterministicFallbackReasoner
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.services.routing_context_builder import RoutingContextBuilder
from app.application.stylist_chat.services.routing_decision_validator import RoutingDecisionValidator
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
from app.domain.chat_modes import ChatMode
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy
from app.domain.style_exploration.policies.semantic_diversity_policy import SemanticDiversityPolicy
from app.domain.style_exploration.policies.visual_diversity_policy import VisualDiversityPolicy
from app.infrastructure.knowledge.caches.knowledge_cache import InMemoryKnowledgeCache
from app.infrastructure.knowledge.repositories.color_theory_repository import DatabaseColorTheoryRepository
from app.infrastructure.knowledge.repositories.fashion_history_repository import DatabaseFashionHistoryRepository
from app.infrastructure.knowledge.repositories.flatlay_patterns_repository import DatabaseFlatlayPatternsRepository
from app.infrastructure.knowledge.repositories.materials_fabrics_repository import DatabaseMaterialsFabricsRepository
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.infrastructure.knowledge.repositories.tailoring_principles_repository import DatabaseTailoringPrinciplesRepository
from app.infrastructure.knowledge.search.knowledge_search_adapter import DefaultKnowledgeSearchAdapter
from app.infrastructure.knowledge.occasion_knowledge_provider import StaticOccasionKnowledgeProvider
from app.infrastructure.knowledge.garment_knowledge_provider import StaticGarmentKnowledgeProvider
from app.infrastructure.llm.llm_garment_extractor import LLMGarmentExtractorAdapter
from app.infrastructure.llm.llm_garment_reasoner import LLMGarmentReasonerAdapter
from app.infrastructure.llm.llm_occasion_extractor import LLMOccasionExtractorAdapter
from app.infrastructure.llm.llm_occasion_reasoner import LLMOccasionReasonerAdapter
from app.infrastructure.llm.vllm_router_client import VllmRouterClient
from app.infrastructure.llm.vllm_reasoner import VLLMReasonerAdapter
from app.infrastructure.observability.structured_event_logger import StructuredEventLogger
from app.infrastructure.observability.structured_metrics_recorder import StructuredMetricsRecorder
from app.infrastructure.persistence.context_checkpoint_writer import SessionContextCheckpointWriter
from app.infrastructure.persistence.style_history_provider import DatabaseStyleHistoryProvider
from app.infrastructure.persistence.stylist_chat_context_store import SessionChatContextStore
from app.infrastructure.queue.generation_job_scheduler import DefaultGenerationJobScheduler
from app.infrastructure.search.static_knowledge_provider import StaticKnowledgeProvider


def build_stylist_chat_orchestrator(session: AsyncSession) -> StylistChatOrchestrator:
    clarification_builder = ClarificationMessageBuilder()
    reasoning_context_builder = ReasoningContextBuilder()
    diversity_constraints_builder = DiversityConstraintsBuilder()
    generation_policy_service = GenerationPolicyService()
    generation_request_builder = GenerationRequestBuilder(
        generation_policy_service=generation_policy_service,
    )
    garment_matching_context_builder = GarmentMatchingContextBuilder()
    garment_brief_compiler = GarmentBriefCompiler()
    occasion_context_builder = OccasionContextBuilder()
    occasion_brief_compiler = OccasionBriefCompiler()
    style_history_service = StyleHistoryService()
    style_exploration_context_builder = StyleExplorationContextBuilder()
    knowledge_query_builder = BuildKnowledgeQueryUseCase()
    knowledge_search_adapter = DefaultKnowledgeSearchAdapter()
    knowledge_bundle_builder = KnowledgeBundleBuilder()
    knowledge_ranker = KnowledgeRanker()
    knowledge_cache = InMemoryKnowledgeCache()

    context_store = SessionChatContextStore(session)
    context_checkpoint_writer = SessionContextCheckpointWriter(context_store)
    routing_context_builder = RoutingContextBuilder()
    fallback_router_policy = FallbackRouterPolicy()
    routing_decision_validator = RoutingDecisionValidator(
        fallback_policy=fallback_router_policy,
    )
    conversation_router = ConversationRouter(
        router_client=VllmRouterClient(),
        routing_context_builder=routing_context_builder,
        decision_validator=routing_decision_validator,
        fallback_policy=fallback_router_policy,
    )
    reasoner = VLLMReasonerAdapter()
    garment_reasoner = LLMGarmentReasonerAdapter()
    occasion_reasoner = LLMOccasionReasonerAdapter()
    fallback_reasoner = DeterministicFallbackReasoner()
    knowledge_provider = StaticKnowledgeProvider()
    garment_knowledge_provider = StaticGarmentKnowledgeProvider()
    occasion_knowledge_provider = StaticOccasionKnowledgeProvider()
    style_catalog_repository = DatabaseStyleCatalogRepository(session)
    knowledge_retrieval_service = DefaultKnowledgeRetrievalService(
        style_catalog_repository=style_catalog_repository,
        color_theory_repository=DatabaseColorTheoryRepository(style_catalog_repository=style_catalog_repository),
        fashion_history_repository=DatabaseFashionHistoryRepository(style_catalog_repository=style_catalog_repository),
        tailoring_principles_repository=DatabaseTailoringPrinciplesRepository(style_catalog_repository=style_catalog_repository),
        materials_fabrics_repository=DatabaseMaterialsFabricsRepository(style_catalog_repository=style_catalog_repository),
        flatlay_patterns_repository=DatabaseFlatlayPatternsRepository(style_catalog_repository=style_catalog_repository),
        knowledge_ranker=knowledge_ranker,
        knowledge_bundle_builder=knowledge_bundle_builder,
        knowledge_search_adapter=knowledge_search_adapter,
        knowledge_cache=knowledge_cache,
    )
    resolve_knowledge_bundle = ResolveKnowledgeBundleUseCase(
        knowledge_retrieval_service=knowledge_retrieval_service,
    )
    inject_knowledge_into_reasoning = InjectKnowledgeIntoReasoningUseCase()
    garment_extractor = LLMGarmentExtractorAdapter()
    occasion_extractor = LLMOccasionExtractorAdapter(reasoner=occasion_reasoner)
    garment_completeness_policy = GarmentCompletenessPolicy()
    garment_clarification_policy = GarmentClarificationPolicy()
    garment_clarification_service = GarmentClarificationService(garment_clarification_policy)
    occasion_completeness_policy = OccasionCompletenessPolicy()
    occasion_clarification_policy = OccasionClarificationPolicy()
    occasion_clarification_service = OccasionClarificationService(occasion_clarification_policy)
    style_history_provider = DatabaseStyleHistoryProvider(
        session,
        style_catalog_repository=style_catalog_repository,
    )
    candidate_style_selector = CandidateStyleSelector(style_history_provider)
    semantic_diversity_service = SemanticDiversityService(SemanticDiversityPolicy())
    visual_diversity_service = VisualDiversityService(VisualDiversityPolicy())
    generation_scheduler = DefaultGenerationJobScheduler(session)
    event_logger = StructuredEventLogger()
    metrics_recorder = StructuredMetricsRecorder()
    conversation_state_policy = ConversationStatePolicy()
    post_action_conversation_policy = PostActionConversationPolicy()
    start_garment_matching = StartGarmentMatchingUseCase(clarification_builder)
    start_occasion_outfit = StartOccasionOutfitUseCase(clarification_builder)
    continue_garment_matching = ContinueGarmentMatchingUseCase(
        garment_extractor=garment_extractor,
        garment_completeness_evaluator=garment_completeness_policy,
        garment_clarification_service=garment_clarification_service,
    )
    update_occasion_context = UpdateOccasionContextUseCase(
        completeness_evaluator=occasion_completeness_policy,
    )
    continue_occasion_outfit = ContinueOccasionOutfitUseCase(
        occasion_context_extractor=occasion_extractor,
        update_occasion_context=update_occasion_context,
        occasion_clarification_service=occasion_clarification_service,
    )
    build_garment_outfit_brief = BuildGarmentOutfitBriefUseCase(
        garment_knowledge_provider=garment_knowledge_provider,
        garment_matching_context_builder=garment_matching_context_builder,
        outfit_brief_builder=garment_brief_compiler,
        garment_brief_compiler=garment_brief_compiler,
        knowledge_query_builder=knowledge_query_builder,
        resolve_knowledge_bundle_use_case=resolve_knowledge_bundle,
        inject_knowledge_into_reasoning_use_case=inject_knowledge_into_reasoning,
    )
    build_occasion_outfit_brief = BuildOccasionOutfitBriefUseCase(
        occasion_knowledge_provider=occasion_knowledge_provider,
        occasion_context_builder=occasion_context_builder,
        outfit_brief_builder=occasion_brief_compiler,
        occasion_brief_compiler=occasion_brief_compiler,
        knowledge_query_builder=knowledge_query_builder,
        resolve_knowledge_bundle_use_case=resolve_knowledge_bundle,
        inject_knowledge_into_reasoning_use_case=inject_knowledge_into_reasoning,
    )
    start_style_exploration = StartStyleExplorationUseCase()
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

    shared_handler_kwargs = {
        "reasoner": reasoner,
        "fallback_reasoner": fallback_reasoner,
        "knowledge_provider": knowledge_provider,
        "reasoning_context_builder": reasoning_context_builder,
        "generation_request_builder": generation_request_builder,
        "knowledge_query_builder": knowledge_query_builder,
        "resolve_knowledge_bundle_use_case": resolve_knowledge_bundle,
        "inject_knowledge_into_reasoning_use_case": inject_knowledge_into_reasoning,
    }
    garment_handler_kwargs = {
        **shared_handler_kwargs,
        "reasoner": garment_reasoner,
    }
    occasion_handler_kwargs = {
        **shared_handler_kwargs,
        "reasoner": occasion_reasoner,
    }
    handlers = {
        ChatMode.GENERAL_ADVICE: GeneralAdviceHandler(**shared_handler_kwargs),
        ChatMode.GARMENT_MATCHING: GarmentMatchingHandler(
            start_use_case=start_garment_matching,
            continue_use_case=continue_garment_matching,
            build_outfit_brief_use_case=build_garment_outfit_brief,
            **garment_handler_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            start_use_case=start_occasion_outfit,
            continue_use_case=continue_occasion_outfit,
            build_outfit_brief_use_case=build_occasion_outfit_brief,
            context_checkpoint_writer=context_checkpoint_writer,
            **occasion_handler_kwargs,
        ),
        ChatMode.STYLE_EXPLORATION: StyleExplorationHandler(
            start_use_case=start_style_exploration,
            select_candidate_style_use_case=select_candidate_style,
            build_diversity_constraints_use_case=build_diversity_constraints,
            build_style_exploration_brief_use_case=build_style_exploration_brief,
            persist_style_direction_use_case=persist_style_direction,
            style_history_service=style_history_service,
            style_history_provider=style_history_provider,
            context_checkpoint_writer=context_checkpoint_writer,
            **shared_handler_kwargs,
        ),
    }

    return StylistChatOrchestrator(
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


__all__ = ["StylistChatOrchestrator", "build_stylist_chat_orchestrator"]
