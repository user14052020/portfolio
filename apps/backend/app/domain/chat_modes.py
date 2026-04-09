from enum import Enum


class ChatMode(str, Enum):
    GENERAL_ADVICE = "general_advice"
    GARMENT_MATCHING = "garment_matching"
    STYLE_EXPLORATION = "style_exploration"
    OCCASION_OUTFIT = "occasion_outfit"


class FlowState(str, Enum):
    IDLE = "idle"
    AWAITING_USER_MESSAGE = "awaiting_user_message"
    AWAITING_ANCHOR_GARMENT = "awaiting_anchor_garment"
    AWAITING_OCCASION_DETAILS = "awaiting_occasion_details"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    READY_FOR_DECISION = "ready_for_decision"
    READY_FOR_GENERATION = "ready_for_generation"
    GENERATION_QUEUED = "generation_queued"
    GENERATION_IN_PROGRESS = "generation_in_progress"
    COMPLETED = "completed"
    RECOVERABLE_ERROR = "recoverable_error"


class ClarificationKind(str, Enum):
    ANCHOR_GARMENT_DESCRIPTION = "anchor_garment_description"
    ANCHOR_GARMENT_MISSING_ATTRIBUTES = "anchor_garment_missing_attributes"
    OCCASION_EVENT_TYPE = "occasion_event_type"
    OCCASION_DRESS_CODE = "occasion_dress_code"
    OCCASION_DESIRED_IMPRESSION = "occasion_desired_impression"
    OCCASION_MISSING_MULTIPLE_SLOTS = "occasion_missing_multiple_slots"
    STYLE_PREFERENCE = "style_preference"
    GENERAL_FOLLOWUP = "general_followup"

