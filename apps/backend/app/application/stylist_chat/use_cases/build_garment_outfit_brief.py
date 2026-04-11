from dataclasses import dataclass
from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import GarmentKnowledgeProvider, KnowledgeResult, OutfitBriefBuilder
from app.domain.knowledge.entities import KnowledgeBundle
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
    knowledge_bundle: KnowledgeBundle | None = None


class BuildGarmentOutfitBriefUseCase:
    def __init__(
        self,
        *,
        garment_knowledge_provider: GarmentKnowledgeProvider,
        garment_matching_context_builder: GarmentMatchingContextBuilder,
        outfit_brief_builder: OutfitBriefBuilder,
        garment_brief_compiler: GarmentBriefCompiler,
        knowledge_query_builder=None,
        resolve_knowledge_bundle_use_case=None,
        inject_knowledge_into_reasoning_use_case=None,
    ) -> None:
        self.garment_knowledge_provider = garment_knowledge_provider
        self.garment_matching_context_builder = garment_matching_context_builder
        self.outfit_brief_builder = outfit_brief_builder
        self.garment_brief_compiler = garment_brief_compiler
        self.knowledge_query_builder = knowledge_query_builder
        self.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle_use_case
        self.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning_use_case

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
        knowledge_bundle = None
        if (
            self.knowledge_query_builder is not None
            and self.resolve_knowledge_bundle_use_case is not None
            and self.inject_knowledge_into_reasoning_use_case is not None
        ):
            knowledge_query = self.knowledge_query_builder.execute(
                command=command,
                context=context,
                mode="garment_matching",
                intent="anchor_garment",
                anchor_garment=garment.model_dump(exclude_none=True),
                limit=6,
            )
            knowledge_bundle = await self.resolve_knowledge_bundle_use_case.execute(query=knowledge_query)
            injected = self.inject_knowledge_into_reasoning_use_case.execute(bundle=knowledge_bundle)
            knowledge_result = injected.knowledge_result
        else:
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
            knowledge_bundle=knowledge_bundle,
        )
