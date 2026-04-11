from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.knowledge.entities import KnowledgeBundle
from app.application.stylist_chat.contracts.ports import (
    FallbackReasonerStrategy,
    KnowledgeResult,
    KnowledgeProvider,
    LLMReasoner,
    LLMReasonerContextLimitError,
    LLMReasonerError,
)
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.application.stylist_chat.services.reasoning_context_builder import ReasoningContextBuilder
from app.domain.chat_context import ChatModeContext, OccasionContext, StyleDirectionContext


class BaseChatModeHandler:
    def __init__(
        self,
        *,
        reasoner: LLMReasoner,
        fallback_reasoner: FallbackReasonerStrategy,
        knowledge_provider: KnowledgeProvider,
        reasoning_context_builder: ReasoningContextBuilder,
        generation_request_builder: GenerationRequestBuilder,
        knowledge_query_builder=None,
        resolve_knowledge_bundle_use_case=None,
        inject_knowledge_into_reasoning_use_case=None,
    ) -> None:
        self.reasoner = reasoner
        self.fallback_reasoner = fallback_reasoner
        self.knowledge_provider = knowledge_provider
        self.reasoning_context_builder = reasoning_context_builder
        self.generation_request_builder = generation_request_builder
        self.knowledge_query_builder = knowledge_query_builder
        self.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle_use_case
        self.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning_use_case

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        raise NotImplementedError

    async def run_reasoning(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        must_generate: bool,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, Any]],
        occasion_context: OccasionContext | None,
        anti_repeat_constraints: dict[str, Any] | None,
        knowledge_mode: str,
        style_history_used: bool,
        structured_outfit_brief: dict[str, Any] | None = None,
        knowledge_result_override: KnowledgeResult | None = None,
        knowledge_bundle_override: KnowledgeBundle | None = None,
    ) -> DecisionResult:
        injected_knowledge = None
        if knowledge_bundle_override is not None and self.inject_knowledge_into_reasoning_use_case is not None:
            injected_knowledge = self.inject_knowledge_into_reasoning_use_case.execute(bundle=knowledge_bundle_override)
            knowledge_result = injected_knowledge.knowledge_result
            context.last_retrieved_knowledge_refs = injected_knowledge.refs
        elif knowledge_result_override is None:
            if self.knowledge_query_builder is not None and self.resolve_knowledge_bundle_use_case is not None:
                knowledge_query = self.knowledge_query_builder.execute(
                    command=command,
                    context=context,
                    mode=knowledge_mode,
                    intent=knowledge_mode,
                    style_id=(style_seed or {}).get("slug") if isinstance(style_seed, dict) else None,
                    style_name=(style_seed or {}).get("title") if isinstance(style_seed, dict) else None,
                    anchor_garment=context.anchor_garment.model_dump(exclude_none=True) if context.anchor_garment else None,
                    occasion_context=occasion_context or context.occasion_context,
                    diversity_constraints=anti_repeat_constraints,
                    limit=6,
                )
                knowledge_bundle = await self.resolve_knowledge_bundle_use_case.execute(query=knowledge_query)
                if self.inject_knowledge_into_reasoning_use_case is not None:
                    injected_knowledge = self.inject_knowledge_into_reasoning_use_case.execute(bundle=knowledge_bundle)
                    knowledge_result = injected_knowledge.knowledge_result
                    context.last_retrieved_knowledge_refs = injected_knowledge.refs
                else:
                    knowledge_result = KnowledgeResult(source="knowledge_layer", query=dict(knowledge_bundle.retrieval_trace))
            else:
                knowledge_query = self.reasoning_context_builder.build_knowledge_query(
                    command=command,
                    context=context,
                    mode=knowledge_mode,
                )
                knowledge_result = await self.knowledge_provider.fetch(query=knowledge_query)
                context.last_retrieved_knowledge_refs = []
        else:
            knowledge_result = knowledge_result_override
            context.last_retrieved_knowledge_refs = []

        reasoning_input = self.reasoning_context_builder.build(
            command=command,
            context=context,
            auto_generate=context.should_auto_generate,
            style_seed=style_seed,
            previous_style_directions=previous_style_directions,
            occasion_context=occasion_context,
            knowledge_result=knowledge_result,
            knowledge_bundle=injected_knowledge.bundle if injected_knowledge is not None else knowledge_bundle_override,
            anti_repeat_constraints=anti_repeat_constraints,
            structured_outfit_brief=structured_outfit_brief,
        )

        fallback_used = False
        try:
            reasoning_output = await self.reasoner.decide(locale=command.locale, reasoning_input=reasoning_input)
        except LLMReasonerContextLimitError:
            decision = self.generation_request_builder.build_recoverable_error(
                context=context,
                locale=command.locale,
                error_code="reasoning_context_limit",
            )
            self._apply_telemetry(
                decision=decision,
                provider="vllm",
                fallback_used=False,
                reasoning_mode="context_limit",
                knowledge_items_count=len(knowledge_result.items),
                style_history_used=style_history_used,
                knowledge_provider_used=knowledge_result.source,
                anchor_garment_confidence=context.anchor_garment.confidence if context.anchor_garment else 0.0,
                anchor_garment_completeness=context.anchor_garment.completeness_score if context.anchor_garment else 0.0,
            )
            if injected_knowledge is not None:
                decision.telemetry.update(injected_knowledge.bundle.retrieval_trace)
            return decision
        except LLMReasonerError:
            reasoning_output = await self.fallback_reasoner.decide(
                locale=command.locale,
                reasoning_input=reasoning_input,
            )
            fallback_used = True

        decision = await self.generation_request_builder.build_from_reasoning(
            command=command,
            context=context,
            reasoning_output=reasoning_output,
            asset_id=command.asset_metadata.get("asset_id"),
            must_generate=must_generate,
            style_seed=style_seed,
            previous_style_directions=previous_style_directions,
            occasion_context=occasion_context,
            anti_repeat_constraints=anti_repeat_constraints,
            structured_outfit_brief=structured_outfit_brief,
            knowledge_cards=[
                {"key": item.key, "text": item.text}
                for item in knowledge_result.items
            ] if injected_knowledge is None else injected_knowledge.knowledge_cards,
            knowledge_bundle=(
                injected_knowledge.bundle.model_dump(mode="json")
                if injected_knowledge is not None
                else knowledge_bundle_override.model_dump(mode="json")
                if knowledge_bundle_override is not None
                else None
            ),
            knowledge_provider_used=knowledge_result.source,
        )
        self._apply_telemetry(
            decision=decision,
            provider=reasoning_output.provider,
            fallback_used=fallback_used,
            reasoning_mode=reasoning_output.reasoning_mode,
            knowledge_items_count=len(knowledge_result.items),
            style_history_used=style_history_used,
            knowledge_provider_used=knowledge_result.source,
            anchor_garment_confidence=context.anchor_garment.confidence if context.anchor_garment else 0.0,
            anchor_garment_completeness=context.anchor_garment.completeness_score if context.anchor_garment else 0.0,
        )
        if injected_knowledge is not None:
            decision.telemetry.update(injected_knowledge.bundle.retrieval_trace)
        return decision

    def style_seed_from_context(self, style: StyleDirectionContext) -> dict[str, str]:
        mood_bit = style.primary_mood if hasattr(style, "primary_mood") else None
        descriptor_bits = [bit for bit in [style.silhouette, mood_bit, *style.hero_garments[:2]] if bit]
        descriptor = ", ".join(descriptor_bits) or style.style_name or "cohesive style direction"
        return {
            "slug": style.style_id or (style.style_name or "style-direction").lower().replace(" ", "-"),
            "title": style.style_name or "Style Direction",
            "descriptor": descriptor,
            "en": style.style_name or "Style Direction",
            "ru": style.style_name or "Style Direction",
        }

    def _apply_telemetry(
        self,
        *,
        decision,
        provider: str,
        fallback_used: bool,
        reasoning_mode: str,
        knowledge_items_count: int,
        style_history_used: bool,
        knowledge_provider_used: str,
        anchor_garment_confidence: float,
        anchor_garment_completeness: float,
    ) -> None:
        decision.telemetry.update(
            {
                "provider": provider,
                "fallback_used": fallback_used,
                "reasoning_mode": reasoning_mode,
                "knowledge_items_count": knowledge_items_count,
                "style_history_used": style_history_used,
                "knowledge_provider_used": knowledge_provider_used,
                "anchor_garment_confidence": anchor_garment_confidence,
                "anchor_garment_completeness": anchor_garment_completeness,
            }
        )
