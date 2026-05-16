from typing import Literal


StyleSelectionStrategy = Literal["profiled", "random"]
DEFAULT_STYLE_SELECTION_STRATEGY: StyleSelectionStrategy = "profiled"


def normalize_style_selection_strategy(value: object) -> StyleSelectionStrategy:
    if isinstance(value, str) and value.strip().lower() == "random":
        return "random"
    return DEFAULT_STYLE_SELECTION_STRATEGY
