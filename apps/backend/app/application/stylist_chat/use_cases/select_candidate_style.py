from dataclasses import dataclass

from app.application.stylist_chat.services.candidate_style_selector import CandidateStyleSelector
from app.application.stylist_chat.services.style_history_service import StyleHistoryService
from app.domain.style_exploration.entities.style_direction import StyleDirection


@dataclass(slots=True)
class SelectedCandidateStyle:
    history: list[StyleDirection]
    candidate_style: StyleDirection
    source_model: object | None


class SelectCandidateStyleUseCase:
    def __init__(
        self,
        *,
        candidate_selector: CandidateStyleSelector,
        style_history_provider,
        style_history_service: StyleHistoryService,
    ) -> None:
        self.candidate_selector = candidate_selector
        self.style_history_provider = style_history_provider
        self.style_history_service = style_history_service

    async def execute(
        self,
        *,
        session_id: str,
        current_history: list[StyleDirection],
    ) -> SelectedCandidateStyle:
        persisted_history = await self.style_history_provider.get_recent(session_id)
        history = self.style_history_service.merge(
            context_history=current_history,
            persisted_history=persisted_history,
        )
        candidate_style, source_model = await self.candidate_selector.select(
            session_id=session_id,
            style_history=history,
        )
        return SelectedCandidateStyle(
            history=history,
            candidate_style=candidate_style,
            source_model=source_model,
        )
