from typing import Any

from app.application.reasoning.contracts import FashionReasoningPipeline, ReasoningOutputMapper
from app.application.reasoning.services.fashion_reasoning_pipeline import DefaultFashionReasoningPipeline
from app.application.reasoning.services.reasoning_output_mapper import DefaultReasoningOutputMapper
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
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints


class FashionReasoningPipelineDecisionAdapter:
    def __init__(
        self,
        *,
        reasoning_pipeline: FashionReasoningPipeline | None = None,
        reasoning_output_mapper: ReasoningOutputMapper | None = None,
        generation_request_builder: GenerationRequestBuilder | None = None,
    ) -> None:
        self.reasoning_pipeline = reasoning_pipeline or DefaultFashionReasoningPipeline()
        self.reasoning_output_mapper = reasoning_output_mapper or DefaultReasoningOutputMapper()
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
                anti_repeat_constraints=anti_repeat_constraints,
                structured_outfit_brief=structured_outfit_brief,
            ),
            profile_context=profile_context,
            retrieval_profile=routing_decision.retrieval_profile,
        )
        presentation_payload = self.reasoning_output_mapper.to_presentation(reasoning_output)

        if reasoning_output.requires_clarification():
            decision = DecisionResult(
                decision_type=DecisionType.CLARIFICATION_REQUIRED,
                active_mode=context.active_mode,
                flow_state=FlowState.AWAITING_CLARIFICATION,
                text_reply=(
                    presentation_payload.voice.clarification_question
                    or presentation_payload.voice.draft_text
                ),
                telemetry=self._telemetry(
                    reasoning_output=reasoning_output,
                    presentation_payload=presentation_payload,
                ),
            )
            return decision

        fashion_brief = reasoning_output.fashion_brief
        structured_brief = self._structured_brief_for_handoff(
            fashion_brief=fashion_brief,
            structured_outfit_brief=structured_outfit_brief,
        )
        legacy_output = self._legacy_reasoning_output(
            reasoning_output=reasoning_output,
            fashion_brief=fashion_brief,
            voice_text=presentation_payload.voice.draft_text,
        )

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
        decision.telemetry.update(
            self._telemetry(
                reasoning_output=reasoning_output,
                presentation_payload=presentation_payload,
            )
        )
        if reasoning_output.can_offer_visualization and not decision.requires_generation():
            if not decision.can_offer_visualization:
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
        anti_repeat_constraints: dict[str, Any] | None,
        structured_outfit_brief: dict[str, Any] | None,
    ) -> SessionStateSnapshot:
        return SessionStateSnapshot(
            user_request=command.normalized_message(),
            recent_conversation_summary=self._conversation_summary(context),
            active_slots=self._active_slots(
                context=context,
                occasion_context=occasion_context,
                structured_outfit_brief=structured_outfit_brief,
            ),
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
            diversity_constraints=self._diversity_constraints(anti_repeat_constraints),
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
        structured_outfit_brief: dict[str, Any] | None,
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
        slots.update(self._structured_brief_slots(structured_outfit_brief))
        return {key: value for key, value in slots.items() if value}

    def _structured_brief_slots(self, structured_outfit_brief: dict[str, Any] | None) -> dict[str, str]:
        if not structured_outfit_brief:
            return {}

        slots: dict[str, str] = {}
        self._put_slot(slots, "brief_type", structured_outfit_brief.get("brief_type"))
        self._put_slot(slots, "anchor_summary", structured_outfit_brief.get("anchor_summary"))
        self._put_slot(slots, "styling_goal", structured_outfit_brief.get("styling_goal"))
        self._put_slot(slots, "style_direction", structured_outfit_brief.get("style_direction"))
        self._put_slot(slots, "style_direction", structured_outfit_brief.get("style_identity"))

        anchor_garment = structured_outfit_brief.get("anchor_garment")
        if isinstance(anchor_garment, dict):
            self._put_slot(slots, "anchor_garment", anchor_garment.get("garment_type"))
            self._put_slot(slots, "anchor_category", anchor_garment.get("category"))
            self._put_slot(slots, "anchor_color", anchor_garment.get("color_primary"))
            self._put_slot(slots, "anchor_material", anchor_garment.get("material"))
            self._put_slot(slots, "anchor_fit", anchor_garment.get("fit"))

        occasion_payload = structured_outfit_brief.get("occasion_context")
        if isinstance(occasion_payload, dict):
            self._put_slot(slots, "occasion", occasion_payload.get("event_type"))
            self._put_slot(slots, "dress_code", occasion_payload.get("dress_code"))
            self._put_slot(slots, "location", occasion_payload.get("location"))
            self._put_slot(slots, "time_of_day", occasion_payload.get("time_of_day"))
            self._put_slot(slots, "desired_impression", occasion_payload.get("desired_impression"))
            self._put_slot(slots, "season", occasion_payload.get("season"))
            self._put_slot(slots, "weather", occasion_payload.get("weather_context"))
            self._put_slot(slots, "weather", occasion_payload.get("season"))

        return slots

    def _put_slot(self, slots: dict[str, str], key: str, value: Any) -> None:
        if key in slots and slots[key]:
            return
        text = self._slot_text(value)
        if text:
            slots[key] = text

    def _slot_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.strip() or None
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, list):
            return ", ".join(str(item).strip() for item in value if str(item).strip()) or None
        return None

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
        voice_text: str | None = None,
    ) -> ReasoningOutput:
        return ReasoningOutput(
            reply_text=(voice_text or reasoning_output.text_response).strip(),
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

    def _structured_brief_for_handoff(
        self,
        *,
        fashion_brief: FashionBrief | None,
        structured_outfit_brief: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        fashion_payload = fashion_brief.model_dump(mode="json") if fashion_brief is not None else None
        if fashion_payload is None:
            return structured_outfit_brief
        if structured_outfit_brief is None:
            return fashion_payload

        merged = dict(structured_outfit_brief)
        merged["reasoning_fashion_brief"] = fashion_payload
        for key, value in fashion_payload.items():
            if self._empty_brief_value(value):
                continue
            existing_value = merged.get(key)
            if self._empty_brief_value(existing_value):
                merged[key] = value
            elif isinstance(existing_value, list) and isinstance(value, list):
                merged[key] = self._dedupe_list([*existing_value, *value])
            elif isinstance(existing_value, dict) and isinstance(value, dict):
                merged[key] = {**value, **existing_value}
            else:
                merged[f"reasoning_{key}"] = value
        return merged

    def _empty_brief_value(self, value: Any) -> bool:
        return value is None or value == "" or value == [] or value == {}

    def _dedupe_list(self, values: list[Any]) -> list[Any]:
        seen: set[str] = set()
        result: list[Any] = []
        for value in values:
            marker = repr(value)
            if marker in seen:
                continue
            seen.add(marker)
            result.append(value)
        return result

    def _diversity_constraints(
        self,
        anti_repeat_constraints: dict[str, Any] | None,
    ) -> DiversityConstraints | None:
        if not anti_repeat_constraints:
            return None
        try:
            return DiversityConstraints.model_validate(anti_repeat_constraints)
        except Exception:
            return None

    def _telemetry(
        self,
        *,
        reasoning_output: FashionReasoningOutput,
        presentation_payload,
    ) -> dict[str, Any]:
        metadata = reasoning_output.reasoning_metadata
        return {
            "reasoning_pipeline_used": True,
            "reasoning_voice_payload_ready": bool(presentation_payload.voice.draft_text),
            "reasoning_generation_handoff_ready": presentation_payload.generation.generation_ready,
            "reasoning_generation_blocked_reason": presentation_payload.generation.blocked_reason,
            "reasoning_voice_style_logic_points_count": len(presentation_payload.voice.style_logic_points),
            "reasoning_voice_visual_language_points_count": len(presentation_payload.voice.visual_language_points),
            "reasoning_response_type": reasoning_output.response_type,
            "reasoning_retrieval_profile": metadata.retrieval_profile,
            "reasoning_used_providers": list(metadata.used_providers),
            "reasoning_style_facets_count": metadata.style_facets_count,
            "reasoning_style_advice_facets_count": metadata.style_advice_facets_count,
            "reasoning_style_image_facets_count": metadata.style_image_facets_count,
            "reasoning_style_visual_language_facets_count": metadata.style_visual_language_facets_count,
            "reasoning_style_relation_facets_count": metadata.style_relation_facets_count,
            "reasoning_style_semantic_fragments_count": metadata.style_semantic_fragments_count,
            "reasoning_profile_alignment_applied": metadata.profile_alignment_applied,
            "reasoning_profile_alignment_filtered_count": reasoning_output.observability.get(
                "profile_alignment_filtered_count"
            ),
            "reasoning_clarification_required": metadata.clarification_required,
            "reasoning_brief_built": metadata.fashion_brief_built,
            "reasoning_cta_offered": metadata.cta_offered,
            "reasoning_generation_ready": metadata.generation_ready,
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
