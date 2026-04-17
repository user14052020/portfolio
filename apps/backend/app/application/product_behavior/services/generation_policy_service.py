from pydantic import BaseModel

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ReasoningOutput
from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.product_behavior.entities.generation_decision import GenerationDecision
from app.domain.product_behavior.policies.conversation_mode_policy import (
    ConversationModePolicy,
    VISUALIZATION_TYPE_FLAT_LAY,
)


class GenerationPolicyInput(BaseModel):
    command: ChatCommand
    context: ChatModeContext
    reasoning_output: ReasoningOutput
    must_generate: bool = False
    has_visualizable_brief: bool = False


class GenerationPolicyService:
    def __init__(self, *, mode_policy: ConversationModePolicy | None = None) -> None:
        self.mode_policy = mode_policy or ConversationModePolicy()

    async def decide(self, context: GenerationPolicyInput) -> GenerationDecision:
        command = context.command
        session_context = context.context
        active_mode = session_context.active_mode
        visualization_type = self.mode_policy.resolve_visualization_type(
            metadata=command.metadata,
            active_mode=active_mode,
        )

        if context.must_generate:
            return GenerationDecision(
                should_generate=True,
                reason="forced_generation",
                visualization_type=visualization_type,
            )

        if self.mode_policy.is_style_exploration_quick_action(
            source=command.source,
            command_name=command.command_name,
            command_step=command.command_step,
        ):
            return GenerationDecision(
                should_generate=True,
                reason="style_exploration_quick_action",
                visualization_type=visualization_type,
            )

        if self.mode_policy.is_visual_confirmation(source=command.source):
            return GenerationDecision(
                should_generate=True,
                reason="cta_confirmation",
                visualization_type=visualization_type,
            )

        if self.mode_policy.explicitly_requests_visualization(message=command.normalized_message()):
            return GenerationDecision(
                should_generate=True,
                reason="explicit_visual_request",
                visualization_type=visualization_type,
            )

        if active_mode in {ChatMode.GARMENT_MATCHING, ChatMode.OCCASION_OUTFIT} and (
            context.has_visualizable_brief or session_context.flow_state == FlowState.READY_FOR_GENERATION
        ):
            return GenerationDecision(
                should_generate=False,
                reason="text_first_visual_cta",
                should_offer_cta=True,
                cta_text=self._cta_text(active_mode=active_mode, locale=command.locale),
                visualization_type=visualization_type,
            )

        if (
            active_mode == ChatMode.GENERAL_ADVICE
            and context.reasoning_output.route == "text_and_generation"
        ):
            return GenerationDecision(
                should_generate=False,
                reason="general_advice_requires_confirmation",
                should_offer_cta=True,
                cta_text=self._cta_text(active_mode=active_mode, locale=command.locale),
                visualization_type=VISUALIZATION_TYPE_FLAT_LAY,
            )

        return GenerationDecision(
            should_generate=False,
            reason="text_first_default",
            visualization_type=visualization_type,
        )

    def _cta_text(self, *, active_mode: ChatMode, locale: str) -> str:
        if locale == "ru":
            if active_mode == ChatMode.GARMENT_MATCHING:
                return "Собрать flat lay вокруг этой вещи?"
            if active_mode == ChatMode.OCCASION_OUTFIT:
                return "Собрать flat lay для этого случая?"
            return "Собрать flat lay референс?"
        if active_mode == ChatMode.GARMENT_MATCHING:
            return "Build a flat lay around this garment?"
        if active_mode == ChatMode.OCCASION_OUTFIT:
            return "Build a flat lay for this occasion?"
        return "Build a flat lay reference?"
