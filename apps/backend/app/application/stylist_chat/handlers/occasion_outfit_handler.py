from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import LLMReasonerError
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.services.clarification_message_builder import ClarificationMessageBuilder
from app.application.stylist_chat.services.constants import (
    DRESS_CODE_KEYWORDS,
    EVENT_TYPE_KEYWORDS,
    IMPRESSION_KEYWORDS,
    LOCATION_KEYWORDS,
    SEASON_KEYWORDS,
    TIME_OF_DAY_KEYWORDS,
    WEATHER_KEYWORDS,
)
from app.domain.chat_context import ChatModeContext, OccasionContext
from app.domain.chat_modes import FlowState
from app.domain.state_machine.occasion_outfit_machine import OccasionOutfitStateMachine

from .base import BaseChatModeHandler


class OccasionOutfitHandler(BaseChatModeHandler):
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
        entry_prompt = self.clarification_builder.occasion_entry_prompt(command.locale)
        if command.command_step == "start":
            OccasionOutfitStateMachine.enter(context, prompt_text=entry_prompt)
            return self.generation_request_builder.build_clarification_decision(
                context=context,
                text=entry_prompt,
            )
        if context.flow_state in {FlowState.IDLE, FlowState.COMPLETED, FlowState.RECOVERABLE_ERROR}:
            OccasionOutfitStateMachine.enter(context, prompt_text=entry_prompt)

        occasion_context = await self.extract_occasion_context(
            locale=command.locale,
            user_message=command.normalized_message(),
            chat_context=context,
            command=command,
            existing_context=context.occasion_context,
        )
        clarification_kind, clarification_text = self.clarification_builder.occasion_clarification(
            command.locale,
            occasion_context,
        )
        OccasionOutfitStateMachine.consume_occasion_context(
            context,
            occasion_context=occasion_context,
            clarification_kind=clarification_kind,
            clarification_text=clarification_text,
        )
        if context.flow_state == FlowState.AWAITING_CLARIFICATION:
            decision = self.generation_request_builder.build_clarification_decision(
                context=context,
                text=context.pending_clarification or entry_prompt,
            )
            return decision

        OccasionOutfitStateMachine.mark_ready_for_generation(context)
        decision = await self.run_reasoning(
            command=command,
            context=context,
            must_generate=True,
            style_seed=None,
            previous_style_directions=[],
            occasion_context=occasion_context,
            anti_repeat_constraints=None,
            knowledge_mode="occasion_outfit",
            style_history_used=False,
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        return decision

    async def extract_occasion_context(
        self,
        *,
        locale: str,
        user_message: str,
        chat_context: ChatModeContext,
        command: ChatCommand,
        existing_context: OccasionContext | None,
    ) -> OccasionContext:
        occasion_context = existing_context.model_copy(deep=True) if existing_context is not None else OccasionContext()
        try:
            extraction = await self.reasoner.extract_occasion_slots(
                locale=locale,
                user_message=user_message,
                conversation_history=self.reasoning_context_builder.build_occasion_extraction_history(
                    context=chat_context,
                    command=command,
                ),
                existing_slots={
                    "event_type": occasion_context.event_type,
                    "venue": occasion_context.location,
                    "dress_code": occasion_context.dress_code,
                    "time_of_day": occasion_context.time_of_day,
                    "season_or_weather": occasion_context.weather_context or occasion_context.season,
                    "desired_impression": occasion_context.desired_impression,
                },
            )
            occasion_context.event_type = extraction.event_type or occasion_context.event_type
            occasion_context.location = extraction.venue or occasion_context.location
            occasion_context.time_of_day = extraction.time_of_day or occasion_context.time_of_day
            if extraction.season_or_weather:
                season_or_weather = extraction.season_or_weather.lower()
                occasion_context.season = (
                    self.first_keyword_match(season_or_weather, SEASON_KEYWORDS) or occasion_context.season
                )
                occasion_context.weather_context = extraction.season_or_weather
            occasion_context.dress_code = extraction.dress_code or occasion_context.dress_code
            occasion_context.desired_impression = extraction.desired_impression or occasion_context.desired_impression
        except LLMReasonerError:
            pass

        lowered = user_message.lower()
        occasion_context.event_type = occasion_context.event_type or self.first_keyword_match(lowered, EVENT_TYPE_KEYWORDS)
        occasion_context.location = occasion_context.location or self.first_keyword_match(lowered, LOCATION_KEYWORDS)
        occasion_context.time_of_day = occasion_context.time_of_day or self.first_keyword_match(lowered, TIME_OF_DAY_KEYWORDS)
        occasion_context.season = occasion_context.season or self.first_keyword_match(lowered, SEASON_KEYWORDS)
        occasion_context.dress_code = occasion_context.dress_code or self.first_keyword_match(lowered, DRESS_CODE_KEYWORDS)
        occasion_context.desired_impression = (
            occasion_context.desired_impression or self.first_keyword_match(lowered, IMPRESSION_KEYWORDS)
        )
        occasion_context.weather_context = (
            occasion_context.weather_context or self.first_keyword_match(lowered, WEATHER_KEYWORDS)
        )
        occasion_context.is_sufficient_for_generation = not bool(occasion_context.missing_core_slots())
        return occasion_context

    def first_keyword_match(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                return canonical
        return None
