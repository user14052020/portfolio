from enum import Enum


class OccasionFlowState(str, Enum):
    IDLE = "idle"
    AWAITING_OCCASION_DETAILS = "awaiting_occasion_details"
    AWAITING_OCCASION_CLARIFICATION = "awaiting_occasion_clarification"
    READY_FOR_DECISION = "ready_for_decision"
    READY_FOR_GENERATION = "ready_for_generation"
    GENERATION_QUEUED = "generation_queued"
    GENERATION_IN_PROGRESS = "generation_in_progress"
    COMPLETED = "completed"
    RECOVERABLE_ERROR = "recoverable_error"
