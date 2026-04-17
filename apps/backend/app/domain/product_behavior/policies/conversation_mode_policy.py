from app.domain.chat_context import ChatModeContext
from app.domain.chat_modes import ChatMode


VISUAL_CONFIRMATION_SOURCES = {"visualization_cta", "explicit_visual_request"}
VISUALIZATION_TYPE_FLAT_LAY = "flat_lay_reference"


class ConversationModePolicy:
    def should_allow_generation(
        self,
        *,
        source: str | None,
        message: str,
        command_name: str | None,
        command_step: str | None,
        active_mode: ChatMode,
        context: ChatModeContext,
    ) -> bool:
        if self.is_style_exploration_quick_action(
            source=source,
            command_name=command_name,
            command_step=command_step,
        ):
            return True
        if self.is_visual_confirmation(source=source):
            return True
        if self.explicitly_requests_visualization(message=message):
            return True
        return False

    def is_style_exploration_quick_action(
        self,
        *,
        source: str | None,
        command_name: str | None,
        command_step: str | None,
    ) -> bool:
        return (
            source == "quick_action"
            and command_name == ChatMode.STYLE_EXPLORATION.value
            and command_step == "start"
        )

    def is_visual_confirmation(self, *, source: str | None) -> bool:
        return source in VISUAL_CONFIRMATION_SOURCES

    def explicitly_requests_visualization(self, *, message: str) -> bool:
        lowered = message.lower()
        if not lowered:
            return False
        return any(
            keyword in lowered
            for keyword in (
                "generate",
                "render",
                "visualize",
                "visualise",
                "lookbook",
                "flat lay",
                "flat-lay",
                "сгенер",
                "визуал",
                "покажи",
            )
        )

    def resolve_visualization_type(
        self,
        *,
        metadata: dict[str, object] | None,
        active_mode: ChatMode,
    ) -> str:
        raw_value = (metadata or {}).get("visualization_type")
        if isinstance(raw_value, str):
            cleaned = raw_value.strip()
            if cleaned:
                return cleaned
        if active_mode in {
            ChatMode.GARMENT_MATCHING,
            ChatMode.OCCASION_OUTFIT,
            ChatMode.STYLE_EXPLORATION,
            ChatMode.GENERAL_ADVICE,
        }:
            return VISUALIZATION_TYPE_FLAT_LAY
        return VISUALIZATION_TYPE_FLAT_LAY
