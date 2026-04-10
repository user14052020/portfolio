from enum import Enum


class GarmentFlowState(str, Enum):
    IDLE = "idle"
    AWAITING_ANCHOR_GARMENT = "awaiting_anchor_garment"
    AWAITING_ANCHOR_GARMENT_CLARIFICATION = "awaiting_anchor_garment_clarification"
    READY_FOR_DECISION = "ready_for_decision"
    READY_FOR_GENERATION = "ready_for_generation"
    GENERATION_QUEUED = "generation_queued"
    GENERATION_IN_PROGRESS = "generation_in_progress"
    COMPLETED = "completed"
    RECOVERABLE_ERROR = "recoverable_error"
