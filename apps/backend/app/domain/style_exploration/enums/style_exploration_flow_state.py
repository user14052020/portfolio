from enum import Enum


class StyleExplorationFlowState(str, Enum):
    STARTED = "started"
    STYLE_SELECTED = "style_selected"
    READY_FOR_GENERATION = "ready_for_generation"
    GENERATION_QUEUED = "generation_queued"
    COMPLETED = "completed"
