from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.application.knowledge.services.knowledge_retrieval_service import DefaultKnowledgeRetrievalService
from app.application.knowledge.use_cases.build_knowledge_query import BuildKnowledgeQueryUseCase
from app.application.knowledge.use_cases.resolve_knowledge_bundle import ResolveKnowledgeBundleUseCase
from app.application.prompt_building.services.prompt_pipeline_builder import PromptPipelineBuilder
from app.application.stylist_chat.contracts.command import ChatCommand
from app.db.session import get_db_session
from app.domain.chat_context import ChatModeContext
from app.infrastructure.knowledge.caches.knowledge_cache import InMemoryKnowledgeCache
from app.infrastructure.knowledge.repositories.color_theory_repository import DatabaseColorTheoryRepository
from app.infrastructure.knowledge.repositories.fashion_history_repository import DatabaseFashionHistoryRepository
from app.infrastructure.knowledge.repositories.flatlay_patterns_repository import DatabaseFlatlayPatternsRepository
from app.infrastructure.knowledge.repositories.materials_fabrics_repository import DatabaseMaterialsFabricsRepository
from app.infrastructure.knowledge.repositories.style_catalog_repository import DatabaseStyleCatalogRepository
from app.infrastructure.knowledge.repositories.tailoring_principles_repository import DatabaseTailoringPrinciplesRepository
from app.infrastructure.knowledge.search.knowledge_search_adapter import DefaultKnowledgeSearchAdapter
from app.schemas.stylist import (
    ChatHistoryPageRead,
    KnowledgePreviewRequest,
    KnowledgePreviewResponse,
    PromptPipelinePreviewRequest,
    PromptPipelinePreviewResponse,
    StylistMessageRequest,
    StylistMessageResponse,
)
from app.services.stylist_conversational import stylist_service


router = APIRouter(prefix="/stylist-chat", tags=["stylist-chat"])


@router.post("/message", response_model=StylistMessageResponse)
async def send_stylist_message(
    payload: StylistMessageRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StylistMessageResponse:
    result = await stylist_service.process_message(session, payload)
    await session.commit()
    return StylistMessageResponse.model_validate(result)


@router.get("/context/{session_id}", response_model=ChatModeContext)
async def get_chat_context(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChatModeContext:
    context = await stylist_service.get_context(session, session_id)
    return ChatModeContext.model_validate(context)


@router.get("/history/{session_id}", response_model=ChatHistoryPageRead)
async def get_chat_history(
    session_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = Query(5, ge=1, le=20),
    before_message_id: int | None = Query(None, ge=1),
) -> ChatHistoryPageRead:
    result = await stylist_service.get_history_page(
        session,
        session_id,
        limit=limit,
        before_message_id=before_message_id,
    )
    return ChatHistoryPageRead.model_validate(result)


@router.post("/debug/prompt-preview", response_model=PromptPipelinePreviewResponse)
async def preview_prompt_pipeline(
    payload: PromptPipelinePreviewRequest,
) -> PromptPipelinePreviewResponse:
    preview = await PromptPipelineBuilder().preview_pipeline(brief=payload.model_dump())
    return PromptPipelinePreviewResponse(
        fashion_brief=preview["fashion_brief"].model_dump(mode="json"),
        compiled_prompt=preview["compiled_prompt"].model_dump(mode="json") if preview["compiled_prompt"] is not None else None,
        generation_payload=preview["generation_payload"].model_dump(mode="json")
        if preview["generation_payload"] is not None
        else None,
        validation_errors=list(preview["validation_errors"]),
    )


@router.post("/debug/knowledge-preview", response_model=KnowledgePreviewResponse)
async def preview_knowledge_bundle(
    payload: KnowledgePreviewRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgePreviewResponse:
    style_catalog_repository = DatabaseStyleCatalogRepository(session)
    retrieval_service = DefaultKnowledgeRetrievalService(
        style_catalog_repository=style_catalog_repository,
        color_theory_repository=DatabaseColorTheoryRepository(style_catalog_repository=style_catalog_repository),
        fashion_history_repository=DatabaseFashionHistoryRepository(style_catalog_repository=style_catalog_repository),
        tailoring_principles_repository=DatabaseTailoringPrinciplesRepository(style_catalog_repository=style_catalog_repository),
        materials_fabrics_repository=DatabaseMaterialsFabricsRepository(style_catalog_repository=style_catalog_repository),
        flatlay_patterns_repository=DatabaseFlatlayPatternsRepository(style_catalog_repository=style_catalog_repository),
        knowledge_ranker=KnowledgeRanker(),
        knowledge_bundle_builder=KnowledgeBundleBuilder(),
        knowledge_search_adapter=DefaultKnowledgeSearchAdapter(),
        knowledge_cache=InMemoryKnowledgeCache(),
    )
    query = BuildKnowledgeQueryUseCase().execute(
        command=ChatCommand(
            session_id=payload.session_id,
            locale=payload.locale,
            message=payload.message,
            profile_context=payload.profile_context,
        ),
        context=ChatModeContext(
            current_style_id=payload.style_id,
            current_style_name=payload.style_name,
        ),
        mode=payload.mode,
        intent=payload.intent,
        style_id=payload.style_id,
        style_name=payload.style_name,
        anchor_garment=payload.anchor_garment,
        occasion_context=payload.occasion_context,
        diversity_constraints=payload.diversity_constraints,
        limit=payload.limit,
    )
    bundle = await ResolveKnowledgeBundleUseCase(
        knowledge_retrieval_service=retrieval_service,
    ).execute(query=query)
    return KnowledgePreviewResponse(
        knowledge_query=query.model_dump(mode="json"),
        knowledge_bundle=bundle.model_dump(mode="json"),
    )
