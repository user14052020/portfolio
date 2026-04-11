from app.application.stylist_chat.contracts.ports import StyleHistoryProvider
from app.domain.style_exploration.entities.style_direction import StyleDirection


class CandidateStyleSelector:
    def __init__(self, style_history_provider: StyleHistoryProvider) -> None:
        self.style_history_provider = style_history_provider

    async def select(
        self,
        *,
        session_id: str,
        style_history: list[StyleDirection],
    ) -> tuple[StyleDirection, object | None]:
        return await self.style_history_provider.pick_next(
            session_id=session_id,
            style_history=style_history,
        )
