from app.domain.style_exploration.entities.style_direction import StyleDirection


class StyleExplorationContextBuilder:
    def build(
        self,
        *,
        style_direction: StyleDirection,
        history: list[StyleDirection],
    ) -> dict[str, object]:
        return {
            "style_direction": style_direction.model_dump(mode="json", exclude_none=True),
            "history_size": len(history),
            "previous_style_ids": [item.style_id for item in history if item.style_id],
            "previous_style_names": [item.style_name for item in history if item.style_name],
        }
