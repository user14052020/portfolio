from dataclasses import dataclass
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import GarmentKnowledgeProvider, KnowledgeResult, OutfitBriefBuilder
from app.application.stylist_chat.services.garment_brief_compiler import GarmentBriefCompiler
from app.application.stylist_chat.services.garment_matching_context_builder import GarmentMatchingContextBuilder
from app.domain.chat_context import ChatModeContext
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.entities.garment_matching_outfit_brief import GarmentMatchingOutfitBrief


@dataclass(slots=True)
class BuildGarmentOutfitBriefResult:
    outfit_brief: GarmentMatchingOutfitBrief
    compiled_brief: dict[str, Any]
    knowledge_result: KnowledgeResult


class BuildGarmentOutfitBriefUseCase:
    def __init__(
        self,
        *,
        garment_knowledge_provider: GarmentKnowledgeProvider,
        garment_matching_context_builder: GarmentMatchingContextBuilder,
        outfit_brief_builder: OutfitBriefBuilder,
        garment_brief_compiler: GarmentBriefCompiler,
    ) -> None:
        self.garment_knowledge_provider = garment_knowledge_provider
        self.garment_matching_context_builder = garment_matching_context_builder
        self.outfit_brief_builder = outfit_brief_builder
        self.garment_brief_compiler = garment_brief_compiler

    async def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        garment: AnchorGarment,
    ) -> BuildGarmentOutfitBriefResult:
        garment_context = self.garment_matching_context_builder.build(
            command=command,
            context=context,
            garment=garment,
        )
        knowledge_result = await self.garment_knowledge_provider.fetch_for_anchor_garment(
            garment=garment,
            context=garment_context,
        )
        outfit_brief = await self.outfit_brief_builder.build(
            garment=garment,
            context=garment_context,
            knowledge_result=knowledge_result,
        )
        return BuildGarmentOutfitBriefResult(
            outfit_brief=outfit_brief,
            compiled_brief=self.garment_brief_compiler.compile(outfit_brief),
            knowledge_result=knowledge_result,
        )
