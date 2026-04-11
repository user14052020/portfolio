from dataclasses import dataclass
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    KnowledgeResult,
    OccasionKnowledgeProvider,
    OccasionOutfitBriefBuilder,
)
from app.domain.knowledge.entities import KnowledgeBundle
from app.application.stylist_chat.services.occasion_brief_compiler import OccasionBriefCompiler
from app.application.stylist_chat.services.occasion_context_builder import OccasionContextBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.entities.occasion_outfit_brief import OccasionOutfitBrief


@dataclass(slots=True)
class BuildOccasionOutfitBriefResult:
    outfit_brief: OccasionOutfitBrief
    compiled_brief: dict[str, Any]
    knowledge_result: KnowledgeResult
    knowledge_bundle: KnowledgeBundle | None = None


class BuildOccasionOutfitBriefUseCase:
    def __init__(
        self,
        *,
        occasion_knowledge_provider: OccasionKnowledgeProvider,
        occasion_context_builder: OccasionContextBuilder,
        outfit_brief_builder: OccasionOutfitBriefBuilder,
        occasion_brief_compiler: OccasionBriefCompiler,
        knowledge_query_builder=None,
        resolve_knowledge_bundle_use_case=None,
        inject_knowledge_into_reasoning_use_case=None,
    ) -> None:
        self.occasion_knowledge_provider = occasion_knowledge_provider
        self.occasion_context_builder = occasion_context_builder
        self.outfit_brief_builder = outfit_brief_builder
        self.occasion_brief_compiler = occasion_brief_compiler
        self.knowledge_query_builder = knowledge_query_builder
        self.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle_use_case
        self.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning_use_case

    async def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        occasion_context: OccasionContext,
    ) -> BuildOccasionOutfitBriefResult:
        occasion_profile_context = self.occasion_context_builder.build(
            command=command,
            context=context,
            occasion_context=occasion_context,
        )
        knowledge_bundle = None
        if (
            self.knowledge_query_builder is not None
            and self.resolve_knowledge_bundle_use_case is not None
            and self.inject_knowledge_into_reasoning_use_case is not None
        ):
            knowledge_query = self.knowledge_query_builder.execute(
                command=command,
                context=context,
                mode="occasion_outfit",
                intent="occasion_slots",
                occasion_context=occasion_context,
                limit=6,
            )
            knowledge_bundle = await self.resolve_knowledge_bundle_use_case.execute(query=knowledge_query)
            injected = self.inject_knowledge_into_reasoning_use_case.execute(bundle=knowledge_bundle)
            knowledge_result = injected.knowledge_result
        else:
            knowledge_result = await self.occasion_knowledge_provider.fetch_for_occasion(
                context=occasion_context,
                profile_context=occasion_profile_context,
            )
        outfit_brief = await self.outfit_brief_builder.build(
            occasion_context=occasion_context,
            context=occasion_profile_context,
            knowledge_result=knowledge_result,
        )
        return BuildOccasionOutfitBriefResult(
            outfit_brief=outfit_brief,
            compiled_brief=self.occasion_brief_compiler.compile(outfit_brief),
            knowledge_result=knowledge_result,
            knowledge_bundle=knowledge_bundle,
        )
