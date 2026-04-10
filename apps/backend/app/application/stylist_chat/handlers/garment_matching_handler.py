from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.constants import (
    COLOR_KEYWORDS,
    FIT_KEYWORDS,
    GARMENT_KEYWORDS,
    MATERIAL_KEYWORDS,
    SEASON_KEYWORDS,
)
from app.domain.chat_context import AnchorGarment, ChatModeContext
from app.domain.chat_modes import FlowState
from app.domain.state_machine.garment_matching_machine import GarmentMatchingStateMachine

from .base import BaseChatModeHandler


class GarmentMatchingHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        clarification_builder: ClarificationMessageBuilder,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.clarification_builder = clarification_builder

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        entry_prompt = self.clarification_builder.garment_entry_prompt(command.locale)
        if command.command_step == "start":
            GarmentMatchingStateMachine.enter(context, prompt_text=entry_prompt)
            return self.generation_request_builder.build_clarification_decision(
                context=context,
                text=entry_prompt,
            )
        if context.flow_state in {FlowState.IDLE, FlowState.COMPLETED, FlowState.RECOVERABLE_ERROR}:
            GarmentMatchingStateMachine.enter(context, prompt_text=entry_prompt)

        anchor = self.extract_anchor_garment(
            user_message=command.normalized_message(),
            asset_name=self.asset_name(command),
            profile_context=command.profile_context,
        )
        if not anchor.raw_user_text and self.asset_name(command) is None:
            decision = self.generation_request_builder.build_clarification_decision(
                context=context,
                text=entry_prompt,
            )
            return decision

        clarification_text = None
        if not anchor.is_sufficient_for_generation:
            clarification_text = self.clarification_builder.garment_clarification_prompt(command.locale, anchor)
        GarmentMatchingStateMachine.consume_anchor_garment(
            context,
            anchor_garment=anchor,
            clarification_text=clarification_text,
        )
        if context.flow_state == FlowState.AWAITING_CLARIFICATION:
            decision = self.generation_request_builder.build_clarification_decision(
                context=context,
                text=context.pending_clarification or entry_prompt,
            )
            return decision

        GarmentMatchingStateMachine.mark_ready_for_generation(context)
        decision = await self.run_reasoning(
            command=command.model_copy(update={"message": anchor.raw_user_text or command.message}),
            context=context,
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=None,
            anti_repeat_constraints=None,
            knowledge_mode="garment_matching",
            style_history_used=False,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision

    def extract_anchor_garment(
        self,
        *,
        user_message: str,
        asset_name: str | None,
        profile_context: dict[str, str | int | None],
    ) -> AnchorGarment:
        raw_text = user_message.strip()
        if not raw_text and asset_name:
            raw_text = asset_name
        lowered = raw_text.lower()

        garment_type = self.first_keyword_match(lowered, GARMENT_KEYWORDS)
        colors = self.all_keyword_matches(lowered, COLOR_KEYWORDS)
        material = self.first_keyword_match(lowered, MATERIAL_KEYWORDS)
        fit = self.first_keyword_match(lowered, FIT_KEYWORDS)
        seasonality = self.first_keyword_match(lowered, SEASON_KEYWORDS)

        confidence = 0.1
        confidence += 0.35 if garment_type else 0.0
        confidence += 0.15 if colors else 0.0
        confidence += 0.15 if material else 0.0
        confidence += 0.15 if fit else 0.0
        confidence += 0.2 if asset_name else 0.0
        return AnchorGarment(
            raw_user_text=raw_text or None,
            garment_type=garment_type,
            color=colors[0] if colors else None,
            secondary_colors=colors[1:] if len(colors) > 1 else [],
            material=material,
            fit=fit,
            silhouette=fit,
            seasonality=seasonality,
            formality=self.infer_formality(lowered),
            gender_context=self.optional_text(profile_context.get("gender")),
            confidence=min(confidence, 0.95),
            is_sufficient_for_generation=bool(asset_name or (garment_type and (colors or material or fit))),
        )

    def infer_formality(self, lowered_text: str) -> str | None:
        if "formal" in lowered_text or "класс" in lowered_text or "вечер" in lowered_text:
            return "formal"
        if "smart casual" in lowered_text or "смарт" in lowered_text:
            return "smart-casual"
        if "casual" in lowered_text or "кэжуал" in lowered_text:
            return "casual"
        return None

    def first_keyword_match(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                return canonical
        return None

    def all_keyword_matches(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
        matches: list[str] = []
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                matches.append(canonical)
        return matches

    def optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def asset_name(self, command: ChatCommand) -> str | None:
        raw_value = command.asset_metadata.get("original_filename")
        if not isinstance(raw_value, str):
            return None
        cleaned = raw_value.strip()
        return cleaned or None
