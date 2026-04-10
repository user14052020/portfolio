from dataclasses import dataclass
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    KnowledgeResult,
    OccasionKnowledgeProvider,
    OccasionOutfitBriefBuilder,
)
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


class BuildOccasionOutfitBriefUseCase:
    def __init__(
        self,
        *,
        occasion_knowledge_provider: OccasionKnowledgeProvider,
        occasion_context_builder: OccasionContextBuilder,
        outfit_brief_builder: OccasionOutfitBriefBuilder,
        occasion_brief_compiler: OccasionBriefCompiler,
    ) -> None:
        self.occasion_knowledge_provider = occasion_knowledge_provider
        self.occasion_context_builder = occasion_context_builder
        self.outfit_brief_builder = outfit_brief_builder
        self.occasion_brief_compiler = occasion_brief_compiler

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
        )
