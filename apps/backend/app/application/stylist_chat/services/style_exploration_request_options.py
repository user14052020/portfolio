from dataclasses import dataclass
from typing import Any

from app.domain.style_exploration.entities.style_selection_strategy import (
    StyleSelectionStrategy,
    normalize_style_selection_strategy,
)


@dataclass(frozen=True, slots=True)
class StyleExplorationRequestOptions:
    selection_strategy: StyleSelectionStrategy = "profiled"

    @property
    def is_random_style(self) -> bool:
        return self.selection_strategy == "random"

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> "StyleExplorationRequestOptions":
        payload = metadata or {}
        strategy = normalize_style_selection_strategy(payload.get("style_selection_strategy"))
        if strategy != "random" and str(payload.get("style_exploration_mode") or "").strip().lower() == "random":
            strategy = "random"
        if strategy != "random" and str(payload.get("quick_action_id") or "").strip().lower() == "random_style":
            strategy = "random"
        return cls(selection_strategy=strategy)

    def default_message(self, locale: str) -> str:
        if self.is_random_style:
            return "\u0421\u043b\u0443\u0447\u0430\u0439\u043d\u044b\u0439 \u0441\u0442\u0438\u043b\u044c" if locale == "ru" else "Random style"
        return "\u041d\u043e\u0432\u044b\u0439 \u0441\u0442\u0438\u043b\u044c" if locale == "ru" else "Try another style"
