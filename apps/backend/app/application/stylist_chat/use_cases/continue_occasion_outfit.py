from dataclasses import dataclass

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import OccasionContextExtractor
from app.application.stylist_chat.services.occasion_clarification_service import OccasionClarificationService
from app.application.stylist_chat.use_cases.update_occasion_context import UpdateOccasionContextUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ClarificationKind
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessAssessment
from app.domain.state_machine.occasion_outfit_machine import OccasionOutfitStateMachine


@dataclass(slots=True)
class ContinueOccasionOutfitResult:
    occasion_context: OccasionContext
    assessment: OccasionCompletenessAssessment
    clarification_kind: ClarificationKind | None
    clarification_text: str | None

    @property
    def is_ready_for_generation(self) -> bool:
        return self.assessment.is_sufficient_for_generation


class ContinueOccasionOutfitUseCase:
    def __init__(
        self,
        *,
        occasion_context_extractor: OccasionContextExtractor,
        update_occasion_context: UpdateOccasionContextUseCase,
        occasion_clarification_service: OccasionClarificationService,
    ) -> None:
        self.occasion_context_extractor = occasion_context_extractor
        self.update_occasion_context = update_occasion_context
        self.occasion_clarification_service = occasion_clarification_service

    async def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> ContinueOccasionOutfitResult:
        occasion_context = await self.occasion_context_extractor.extract(
            locale=command.locale,
            user_message=command.normalized_message(),
            context=context,
            existing_context=context.occasion_context,
            asset_metadata=command.asset_metadata,
            fallback_history=command.fallback_history,
        )
        assessment = self.update_occasion_context.execute(occasion_context=occasion_context)
        clarification_kind = None
        clarification_text = None
        if assessment.is_sufficient_for_generation:
            OccasionOutfitStateMachine.consume_occasion_context(
                context,
                occasion_context=occasion_context,
                clarification_kind=None,
                clarification_text=None,
            )
        else:
            clarification_kind, clarification_text = self.occasion_clarification_service.build(
                locale=command.locale,
                context=occasion_context,
                assessment=assessment,
            )
            OccasionOutfitStateMachine.consume_occasion_context(
                context,
                occasion_context=occasion_context,
                clarification_kind=clarification_kind,
                clarification_text=clarification_text,
            )
        return ContinueOccasionOutfitResult(
            occasion_context=occasion_context,
            assessment=assessment,
            clarification_kind=clarification_kind,
            clarification_text=clarification_text,
        )
