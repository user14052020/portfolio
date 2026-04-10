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
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.domain.chat_modes import ChatMode
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

    context_store = SessionChatContextStore(session)
    mode_resolver = chat_mode_resolver
    reasoner = VLLMReasonerAdapter()
    fallback_reasoner = DeterministicFallbackReasoner()
    knowledge_provider = StaticKnowledgeProvider()
    style_history_provider = DatabaseStyleHistoryProvider(session)
    generation_scheduler = DefaultGenerationJobScheduler(session)
    event_logger = StructuredEventLogger()

    shared_handler_kwargs = {
        "reasoner": reasoner,
        "fallback_reasoner": fallback_reasoner,
        "knowledge_provider": knowledge_provider,
        "reasoning_context_builder": reasoning_context_builder,
        "generation_request_builder": generation_request_builder,
    }
    handlers = {
        ChatMode.GENERAL_ADVICE: GeneralAdviceHandler(**shared_handler_kwargs),
        ChatMode.GARMENT_MATCHING: GarmentMatchingHandler(
            clarification_builder=clarification_builder,
            **shared_handler_kwargs,
        ),
        ChatMode.OCCASION_OUTFIT: OccasionOutfitHandler(
            clarification_builder=clarification_builder,
            **shared_handler_kwargs,
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
