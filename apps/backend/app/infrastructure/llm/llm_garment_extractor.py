from app.application.stylist_chat.services.garment_extraction_service import RuleBasedGarmentExtractor


class LLMGarmentExtractorAdapter(RuleBasedGarmentExtractor):
    """Dedicated adapter slot for garment extraction."""

