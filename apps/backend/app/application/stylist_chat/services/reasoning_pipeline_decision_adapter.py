from typing import Any

from app.application.reasoning.contracts import FashionReasoningPipeline
from app.application.reasoning.services.fashion_reasoning_pipeline import DefaultFashionReasoningPipeline
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ReasoningOutput
from app.application.stylist_chat.results.decision_result import DecisionResult, DecisionType
from app.application.stylist_chat.services.generation_request_builder import GenerationRequestBuilder
from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.chat_modes import FlowState
from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.product_behavior.entities.visualization_offer import VisualizationOffer
from app.domain.reasoning import (
    FashionReasoningOutput,
    ProfileContextSnapshot,
    SessionStateSnapshot,
    UsedStyleReference,
)
from app.domain.routing import RoutingDecision, RoutingMode


class FashionReasoningPipelineDecisionAdapter:
    def __init__(
        self,
        *,
        reasoning_pipeline: FashionReasoningPipeline | None = None,
        generation_request_builder: GenerationRequestBuilder | None = None,
    ) -> None:
        self.reasoning_pipeline = reasoning_pipeline or DefaultFashionReasoningPipeline()
        self.generation_request_builder = generation_request_builder or GenerationRequestBuilder()

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        must_generate: bool,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, Any]],
        occasion_context: OccasionContext | None,
        anti_repeat_constraints: dict[str, Any] | None,
        structured_outfit_brief: dict[str, Any] | None = None,
    ) -> DecisionResult:
        routing_decision = self._routing_decision(command=command, context=context, must_generate=must_generate)
        profile_context = self._profile_context(command)
        reasoning_output = await self.reasoning_pipeline.run(
            routing_decision=routing_decision,
            session_state=self._session_state(
                command=command,
                context=context,
                occasion_context=occasion_context,
            ),
            profile_context=profile_context,
            retrieval_profile=routing_decision.retrieval_profile,
        )

        if reasoning_output.requires_clarification():
            decision = DecisionResult(
                decision_type=DecisionType.CLARIFICATION_REQUIRED,
                active_mode=context.active_mode,
                flow_state=FlowState.AWAITING_CLARIFICATION,
                text_reply=reasoning_output.clarification_question or reasoning_output.text_response,
                telemetry=self._telemetry(reasoning_output),
            )
            return decision

        fashion_brief = reasoning_output.fashion_brief
        structured_brief = (
            fashion_brief.model_dump(mode="json")
            if fashion_brief is not None
            else structured_outfit_brief
        )
        legacy_output = self._legacy_reasoning_output(reasoning_output=reasoning_output, fashion_brief=fashion_brief)

        decision = await self.generation_request_builder.build_from_reasoning(
            command=command,
            context=context,
            reasoning_output=legacy_output,
            asset_id=self._asset_id(command),
            must_generate=must_generate,
            style_seed=style_seed,
            previous_style_directions=previous_style_directions,
            occasion_context=occasion_context,
            anti_repeat_constraints=anti_repeat_constraints,
            structured_outfit_brief=structured_brief,
            knowledge_cards=self._knowledge_cards(fashion_brief),
            knowledge_bundle=None,
            knowledge_provider_used=self._knowledge_provider(reasoning_output),
        )
        decision.telemetry.update(self._telemetry(reasoning_output))
        if reasoning_output.can_offer_visualization and not decision.can_offer_visualization and not decision.requires_generation():
            decision.apply_visualization_offer(
                VisualizationOffer(
                    can_offer_visualization=True,
                    cta_text=reasoning_output.suggested_cta,
                    visualization_type="flat_lay_reference",
                )
            )
            decision.flow_state = FlowState.READY_FOR_GENERATION
        return decision

    def _routing_decision(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        must_generate: bool,
    ) -> RoutingDecision:
        metadata = context.command_context.metadata if context.command_context is not None else {}
        raw_decision = metadata.get("routing_decision")
        if isinstance(raw_decision, dict):
            try:
                return RoutingDecision.model_validate(raw_decision)
            except Exception:
                pass
        return RoutingDecision(
            mode=RoutingMode(context.active_mode.value),
            generation_intent=must_generate or self._can_generate_now(command),
            retrieval_profile=self._optional_text(metadata.get("routing_retrieval_profile")),
        )

    def _session_state(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        occasion_context: OccasionContext | None,
    ) -> SessionStateSnapshot:
        return SessionStateSnapshot(
            user_request=command.normalized_message(),
            recent_conversation_summary=self._conversation_summary(context),
            active_slots=self._active_slots(context=context, occasion_context=occasion_context),
            can_generate_now=self._can_generate_now(command),
            locale=command.locale,
            current_style_id=context.current_style_id,
            current_style_name=context.current_style_name,
            style_history=[
                UsedStyleReference(
                    style_id=style.style_id,
                    style_name=style.style_name,
                    style_cluster=style.style_family,
                    palette=list(style.palette),
                    hero_garments=list(style.hero_garments),
                    visual_motifs=list(style.styling_mood),
                )
                for style in context.style_history[-5:]
            ],
            metadata={
                **dict(command.metadata),
                "session_id": command.session_id,
                "message_id": command.user_message_id,
                "asset_id": command.asset_id,
            },
        )

    def _profile_context(self, command: ChatCommand) -> ProfileContextSnapshot | None:
        values = {key: value for key, value in command.profile_context.items() if value is not None}
        if not values:
            return None
        return ProfileContextSnapshot(values=values, present=True, source="chat_command")

    def _active_slots(
        self,
        *,
        context: ChatModeContext,
        occasion_context: OccasionContext | None,
    ) -> dict[str, str]:
        slots: dict[str, str] = {}
        effective_occasion = occasion_context or context.occasion_context
        if effective_occasion is not None:
            for key, value in effective_occasion.model_dump(exclude_none=True).items():
                if isinstance(value, str) and value.strip():
                    slots[key] = value.strip()
            if effective_occasion.event_type:
                slots["occasion"] = effective_occasion.event_type
            if effective_occasion.weather_context or effective_occasion.season:
                slots["weather"] = effective_occasion.weather_context or effective_occasion.season or ""
        if context.anchor_garment is not None:
            anchor = context.anchor_garment
            if anchor.garment_type:
                slots["anchor_garment"] = anchor.garment_type
        return {key: value for key, value in slots.items() if value}

    def _conversation_summary(self, context: ChatModeContext) -> str | None:
        items = context.conversation_memory[-5:]
        if not items:
            return None
        summary = "\n".join(f"{item.role}: {item.content}" for item in items)
        return summary or None

    def _legacy_reasoning_output(
        self,
        *,
        reasoning_output: FashionReasoningOutput,
        fashion_brief: FashionBrief | None,
    ) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text=reasoning_output.text_response,
            image_brief_en=self._image_brief(fashion_brief),
            route="text_and_generation" if reasoning_output.can_offer_visualization else "text_only",
            provider="fashion_reasoning_pipeline",
            raw_content="",
            reasoning_mode=reasoning_output.response_type,
        )

    def _image_brief(self, fashion_brief: FashionBrief | None) -> str:
        if fashion_brief is None:
            return "cohesive editorial flat lay outfit"
        bits = [
            fashion_brief.style_identity or fashion_brief.style_direction,
            ", ".join(fashion_brief.hero_garments or fashion_brief.garment_list[:3]),
            ", ".join(fashion_brief.palette[:4]),
            "; ".join(fashion_brief.composition_rules[:2]),
        ]
        return " | ".join(bit for bit in bits if bit) or "cohesive editorial flat lay outfit"

    def _knowledge_cards(self, fashion_brief: FashionBrief | None) -> list[dict[str, Any]]:
        if fashion_brief is None:
            return []
        return list(fashion_brief.knowledge_cards)

    def _knowledge_provider(self, reasoning_output: FashionReasoningOutput) -> str:
        providers = reasoning_output.reasoning_metadata.used_providers
        if providers:
            return ",".join(providers)
        return "reasoning_pipeline"

    def _telemetry(self, reasoning_output: FashionReasoningOutput) -> dict[str, Any]:
        return {
            "reasoning_pipeline_used": True,
            "reasoning_response_type": reasoning_output.response_type,
            "reasoning_retrieval_profile": reasoning_output.reasoning_metadata.retrieval_profile,
            "reasoning_style_facets_count": reasoning_output.reasoning_metadata.style_facets_count,
            "reasoning_profile_alignment_applied": reasoning_output.reasoning_metadata.profile_alignment_applied,
            "reasoning_brief_built": reasoning_output.reasoning_metadata.fashion_brief_built,
            "reasoning_cta_offered": reasoning_output.reasoning_metadata.cta_offered,
            "reasoning_generation_ready": reasoning_output.reasoning_metadata.generation_ready,
            **dict(reasoning_output.observability),
        }

    def _can_generate_now(self, command: ChatCommand) -> bool:
        if command.source in {"visualization_cta", "explicit_visual_request"}:
            return True
        if command.source == "quick_action" and command.command_name == "style_exploration":
            return True
        return self.generation_request_builder.explicitly_requests_generation(command.normalized_message())

    def _asset_id(self, command: ChatCommand) -> int | None:
        if isinstance(command.asset_id, int):
            return command.asset_id
        if isinstance(command.asset_id, str) and command.asset_id.strip().isdigit():
            return int(command.asset_id.strip())
        raw_asset_id = command.asset_metadata.get("asset_id")
        if isinstance(raw_asset_id, int):
            return raw_asset_id
        if isinstance(raw_asset_id, str) and raw_asset_id.strip().isdigit():
            return int(raw_asset_id.strip())
        return None

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None
