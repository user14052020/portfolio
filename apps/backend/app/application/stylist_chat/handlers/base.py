from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    FallbackReasonerStrategy,
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
    ) -> None:
        self.reasoner = reasoner
        self.fallback_reasoner = fallback_reasoner
        self.knowledge_provider = knowledge_provider
        self.reasoning_context_builder = reasoning_context_builder
        self.generation_request_builder = generation_request_builder

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
        previous_style_directions: list[dict[str, str]],
        occasion_context: OccasionContext | None,
        anti_repeat_constraints: dict[str, list[str]] | None,
        knowledge_mode: str,
        style_history_used: bool,
    ) -> DecisionResult:
        knowledge_query = self.reasoning_context_builder.build_knowledge_query(
            command=command,
            context=context,
            mode=knowledge_mode,
        )
        knowledge_result = await self.knowledge_provider.fetch(query=knowledge_query)
        reasoning_input = self.reasoning_context_builder.build(
            command=command,
            context=context,
            auto_generate=context.should_auto_generate,
            style_seed=style_seed,
            previous_style_directions=previous_style_directions,
            occasion_context=occasion_context,
            knowledge_result=knowledge_result,
            anti_repeat_constraints=anti_repeat_constraints,
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
            )
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
            occasion_context=occasion_context,
        )
        self._apply_telemetry(
            decision=decision,
            provider=reasoning_output.provider,
            fallback_used=fallback_used,
            reasoning_mode=reasoning_output.reasoning_mode,
            knowledge_items_count=len(knowledge_result.items),
            style_history_used=style_history_used,
        )
        return decision

    def style_seed_from_context(self, style: StyleDirectionContext) -> dict[str, str]:
        descriptor_bits = [bit for bit in [style.silhouette, style.styling_mood, *style.hero_garments[:2]] if bit]
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
    ) -> None:
        decision.telemetry.update(
            {
                "provider": provider,
                "fallback_used": fallback_used,
                "reasoning_mode": reasoning_mode,
                "knowledge_items_count": knowledge_items_count,
                "style_history_used": style_history_used,
            }
        )
