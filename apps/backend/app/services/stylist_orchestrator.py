from sqlalchemy.ext.asyncio import AsyncSession

from app.application.stylist_chat.handlers.garment_matching_handler import GarmentMatchingHandler
from app.application.stylist_chat.handlers.general_advice_handler import GeneralAdviceHandler
from app.application.stylist_chat.handlers.occasion_outfit_handler import OccasionOutfitHandler
from app.application.stylist_chat.handlers.style_exploration_handler import StyleExplorationHandler
from app.application.stylist_chat.orchestrator.command_dispatcher import CommandDispatcher
from app.application.stylist_chat.orchestrator.mode_router import ModeRouter
from app.application.stylist_chat.orchestrator.stylist_chat_orchestrator import StylistChatOrchestrator
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.diversity_constraints_builder import DiversityConstraintsBuilder
from app.application.stylist_chat.services.fallback_reasoner import DeterministicFallbackReasoner
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.application.stylist_chat.use_cases.build_garment_outfit_brief import BuildGarmentOutfitBriefUseCase
from app.application.stylist_chat.use_cases.build_occasion_outfit_brief import BuildOccasionOutfitBriefUseCase
from app.application.stylist_chat.use_cases.continue_garment_matching import ContinueGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.continue_occasion_outfit import ContinueOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.start_garment_matching import StartGarmentMatchingUseCase
from app.application.stylist_chat.use_cases.start_occasion_outfit import StartOccasionOutfitUseCase
from app.application.stylist_chat.use_cases.update_occasion_context import UpdateOccasionContextUseCase
from app.domain.chat_modes import ChatMode
from app.domain.garment_matching.policies.garment_clarification_policy import GarmentClarificationPolicy
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessPolicy
from app.domain.occasion_outfit.policies.occasion_clarification_policy import OccasionClarificationPolicy
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessPolicy
from app.infrastructure.knowledge.occasion_knowledge_provider import StaticOccasionKnowledgeProvider
from app.infrastructure.knowledge.garment_knowledge_provider import StaticGarmentKnowledgeProvider
from app.infrastructure.llm.llm_garment_extractor import LLMGarmentExtractorAdapter
from app.infrastructure.llm.llm_garment_reasoner import LLMGarmentReasonerAdapter
from app.infrastructure.llm.llm_occasion_extractor import LLMOccasionExtractorAdapter
from app.infrastructure.llm.llm_occasion_reasoner import LLMOccasionReasonerAdapter
from app.infrastructure.llm.vllm_reasoner import VLLMReasonerAdapter
from app.infrastructure.observability.structured_event_logger import StructuredEventLogger
from app.infrastructure.persistence.style_history_provider import DatabaseStyleHistoryProvider
from app.infrastructure.persistence.stylist_chat_context_store import SessionChatContextStore
from app.infrastructure.queue.generation_job_scheduler import DefaultGenerationJobScheduler
from app.infrastructure.search.static_knowledge_provider import StaticKnowledgeProvider
from app.services.chat_mode_resolver import chat_mode_resolver


def build_stylist_chat_orchestrator(session: AsyncSession) -> StylistChatOrchestrator:
    clarification_builder = ClarificationMessageBuilder()
    reasoning_context_builder = ReasoningContextBuilder()
    diversity_constraints_builder = DiversityConstraintsBuilder()
    generation_request_builder = GenerationRequestBuilder()
    garment_matching_context_builder = GarmentMatchingContextBuilder()
    garment_brief_compiler = GarmentBriefCompiler()
    occasion_context_builder = OccasionContextBuilder()
    occasion_brief_compiler = OccasionBriefCompiler()

    context_store = SessionChatContextStore(session)
    mode_resolver = chat_mode_resolver
    reasoner = VLLMReasonerAdapter()
    garment_reasoner = LLMGarmentReasonerAdapter()
    occasion_reasoner = LLMOccasionReasonerAdapter()
    fallback_reasoner = DeterministicFallbackReasoner()
    knowledge_provider = StaticKnowledgeProvider()
    garment_knowledge_provider = StaticGarmentKnowledgeProvider()
    occasion_knowledge_provider = StaticOccasionKnowledgeProvider()
    garment_extractor = LLMGarmentExtractorAdapter()
    occasion_extractor = LLMOccasionExtractorAdapter(reasoner=occasion_reasoner)
    garment_completeness_policy = GarmentCompletenessPolicy()
    garment_clarification_policy = GarmentClarificationPolicy()
    garment_clarification_service = GarmentClarificationService(garment_clarification_policy)
    occasion_completeness_policy = OccasionCompletenessPolicy()
    occasion_clarification_policy = OccasionClarificationPolicy()
    occasion_clarification_service = OccasionClarificationService(occasion_clarification_policy)
    style_history_provider = DatabaseStyleHistoryProvider(session)
    generation_scheduler = DefaultGenerationJobScheduler(session)
    event_logger = StructuredEventLogger()
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
    )
    build_occasion_outfit_brief = BuildOccasionOutfitBriefUseCase(
        occasion_knowledge_provider=occasion_knowledge_provider,
        occasion_context_builder=occasion_context_builder,
        outfit_brief_builder=occasion_brief_compiler,
        occasion_brief_compiler=occasion_brief_compiler,
    )

    shared_handler_kwargs = {
        "reasoner": reasoner,
        "fallback_reasoner": fallback_reasoner,
        "knowledge_provider": knowledge_provider,
        "reasoning_context_builder": reasoning_context_builder,
        "generation_request_builder": generation_request_builder,
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
            generation_scheduler=generation_scheduler,
            **garment_handler_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            start_use_case=start_occasion_outfit,
            continue_use_case=continue_occasion_outfit,
            build_outfit_brief_use_case=build_occasion_outfit_brief,
            generation_scheduler=generation_scheduler,
            **occasion_handler_kwargs,
        ),
        ChatMode.STYLE_EXPLORATION: StyleExplorationHandler(
            style_history_provider=style_history_provider,
            diversity_constraints_builder=diversity_constraints_builder,
            **shared_handler_kwargs,
        ),
    }

    return StylistChatOrchestrator(
        context_store=context_store,
        generation_scheduler=generation_scheduler,
        event_logger=event_logger,
        command_dispatcher=CommandDispatcher(mode_resolver=mode_resolver),
        mode_router=ModeRouter(handlers=handlers),
        generation_request_builder=generation_request_builder,
    )


__all__ = ["StylistChatOrchestrator", "build_stylist_chat_orchestrator"]
