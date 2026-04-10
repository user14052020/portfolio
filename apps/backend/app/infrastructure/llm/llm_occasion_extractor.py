from app.application.stylist_chat.services.occasion_extraction_service import OccasionExtractionService
from app.infrastructure.llm.vllm_reasoner import VLLMReasonerAdapter


class LLMOccasionExtractorAdapter(OccasionExtractionService):
    def __init__(self, *, reasoner=None) -> None:
        super().__init__(reasoner=reasoner or VLLMReasonerAdapter())
