from dataclasses import dataclass

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import GarmentCompletenessEvaluator, GarmentExtractor
from app.application.stylist_chat.services.garment_clarification_service import GarmentClarificationService
from app.domain.chat_context import ChatModeContext
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.policies.garment_completeness_policy import GarmentCompletenessAssessment
from app.domain.state_machine.garment_matching_machine import GarmentMatchingStateMachine


@dataclass(slots=True)
class ContinueGarmentMatchingResult:
    anchor_garment: AnchorGarment
    assessment: GarmentCompletenessAssessment
    clarification_text: str | None

    @property
    def is_ready_for_generation(self) -> bool:
        return self.assessment.is_sufficient_for_generation


class ContinueGarmentMatchingUseCase:
    def __init__(
        self,
        *,
        garment_extractor: GarmentExtractor,
        garment_completeness_evaluator: GarmentCompletenessEvaluator,
        garment_clarification_service: GarmentClarificationService,
    ) -> None:
        self.garment_extractor = garment_extractor
        self.garment_completeness_evaluator = garment_completeness_evaluator
        self.garment_clarification_service = garment_clarification_service

    async def execute(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> ContinueGarmentMatchingResult:
        user_text = command.normalized_message()
        asset_name = command.asset_metadata.get("original_filename")
        if not user_text and isinstance(asset_name, str) and asset_name.strip():
            user_text = asset_name.strip()
        anchor = await self.garment_extractor.extract(
            user_text=user_text,
            asset_id=str(command.asset_id) if command.asset_id is not None else None,
            existing_anchor=context.anchor_garment,
        )
        profile_gender = command.profile_context.get("gender")
        if anchor.gender_context is None and isinstance(profile_gender, str) and profile_gender.strip():
            anchor.gender_context = profile_gender.strip()
        assessment = self.garment_completeness_evaluator.evaluate(anchor)
        anchor.completeness_score = assessment.completeness_score
        anchor.is_sufficient_for_generation = assessment.is_sufficient_for_generation
        clarification_text = None
        if assessment.is_sufficient_for_generation:
            GarmentMatchingStateMachine.consume_anchor_garment(context, anchor_garment=anchor)
        else:
            _, clarification_text = self.garment_clarification_service.build(
                locale=command.locale,
                garment=anchor,
                assessment=assessment,
            )
            GarmentMatchingStateMachine.consume_anchor_garment(
                context,
                anchor_garment=anchor,
                clarification_text=clarification_text,
            )
        return ContinueGarmentMatchingResult(
            anchor_garment=anchor,
            assessment=assessment,
            clarification_text=clarification_text,
        )
