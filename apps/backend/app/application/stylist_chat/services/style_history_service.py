from app.domain.style_exploration.entities.style_direction import StyleDirection
from app.domain.style_exploration.entities.style_history import StyleHistory


class StyleHistoryService:
    def merge(self, *, context_history: list[StyleDirection], persisted_history: list[StyleDirection]) -> list[StyleDirection]:
        merged = StyleHistory(directions=[item.model_copy(deep=True) for item in persisted_history], limit=5)
        for style in context_history:
            merged.remember(style.model_copy(deep=True))
        return merged.recent()

    def remember(self, *, history: list[StyleDirection], style_direction: StyleDirection) -> list[StyleDirection]:
        next_history = StyleHistory(directions=[item.model_copy(deep=True) for item in history], limit=5)
        next_history.remember(style_direction.model_copy(deep=True))
        return next_history.recent()

    def to_prompt_items(self, history: list[StyleDirection]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        for style in history[-5:]:
            payload = style.model_dump(mode="json", exclude_none=True)
            if not payload.get("style_name"):
                payload["style_name"] = "Style Direction"
            items.append(payload)
        return items
