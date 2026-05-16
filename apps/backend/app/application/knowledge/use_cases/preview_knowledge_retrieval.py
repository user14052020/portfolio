from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.knowledge.contracts import (
    KnowledgeContextAssembler,
    KnowledgeProvidersRegistry,
    KnowledgeRuntimeSettingsProvider,
)
from app.application.knowledge.use_cases.build_knowledge_query import BuildKnowledgeQueryUseCase
from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.knowledge.entities import KnowledgeProviderConfig, KnowledgeQuery, KnowledgeRuntimeFlags
from app.domain.reasoning.entities.knowledge_context import KnowledgeContext


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalPreviewResult:
    knowledge_query: KnowledgeQuery
    knowledge_context: KnowledgeContext
    runtime_flags: KnowledgeRuntimeFlags
    provider_priorities: dict[str, int]
    enabled_runtime_providers: list[KnowledgeProviderConfig]


class PreviewKnowledgeRetrievalUseCase:
    def __init__(
        self,
        *,
        query_builder: BuildKnowledgeQueryUseCase | None = None,
        knowledge_context_assembler: KnowledgeContextAssembler,
        providers_registry: KnowledgeProvidersRegistry,
        runtime_settings_provider: KnowledgeRuntimeSettingsProvider,
    ) -> None:
        self._query_builder = query_builder or BuildKnowledgeQueryUseCase()
        self._knowledge_context_assembler = knowledge_context_assembler
        self._providers_registry = providers_registry
        self._runtime_settings_provider = runtime_settings_provider

    async def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        mode: str,
        intent: str | None = None,
        style_id: str | None = None,
        style_name: str | None = None,
        anchor_garment: dict[str, Any] | None = None,
        occasion_context: OccasionContext | dict[str, Any] | None = None,
        diversity_constraints: dict[str, Any] | None = None,
        limit: int = 6,
        query_overrides: dict[str, Any] | None = None,
    ) -> KnowledgeRetrievalPreviewResult:
        base_query = self._query_builder.execute(
            command=command,
            context=context,
            mode=mode,
            intent=intent,
            style_id=style_id,
            style_name=style_name,
            anchor_garment=anchor_garment,
            occasion_context=occasion_context,
            diversity_constraints=diversity_constraints,
            limit=limit,
        )
        knowledge_query = base_query.model_copy(update=_normalized_query_overrides(query_overrides))
        runtime_flags = await self._runtime_settings_provider.get_runtime_flags()
        provider_priorities = await self._runtime_settings_provider.get_provider_priorities()
        enabled_runtime_providers = [
            provider.config
            for provider in await self._providers_registry.get_enabled_runtime_providers()
        ]
        knowledge_context = await self._knowledge_context_assembler.assemble(knowledge_query)
        return KnowledgeRetrievalPreviewResult(
            knowledge_query=knowledge_query,
            knowledge_context=knowledge_context,
            runtime_flags=runtime_flags,
            provider_priorities=provider_priorities,
            enabled_runtime_providers=enabled_runtime_providers,
        )


def _normalized_query_overrides(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {}
    overrides: dict[str, Any] = {}
    list_fields = {
        "style_ids": [str(item).strip() for item in payload.get("style_ids", []) if str(item).strip()],
        "style_families": [str(item).strip() for item in payload.get("style_families", []) if str(item).strip()],
        "eras": [str(item).strip() for item in payload.get("eras", []) if str(item).strip()],
    }
    for key, values in list_fields.items():
        if values:
            overrides[key] = values
    for field_name in (
        "retrieval_profile",
        "user_request",
    ):
        raw_value = payload.get(field_name)
        if isinstance(raw_value, str) and raw_value.strip():
            overrides[field_name] = raw_value.strip()
    for field_name in (
        "need_visual_knowledge",
        "need_historical_knowledge",
        "need_styling_rules",
        "need_color_poetics",
    ):
        raw_value = payload.get(field_name)
        if isinstance(raw_value, bool):
            overrides[field_name] = raw_value
    return overrides
