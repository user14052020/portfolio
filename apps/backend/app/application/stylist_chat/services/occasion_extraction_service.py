from typing import Any

from app.application.stylist_chat.contracts.ports import LLMReasoner, LLMReasonerError, OccasionContextExtractor
from app.application.stylist_chat.services.constants import (
    COLOR_KEYWORDS,
    DRESS_CODE_KEYWORDS,
    EVENT_TYPE_KEYWORDS,
    GARMENT_KEYWORDS,
    IMPRESSION_KEYWORDS,
    LOCATION_KEYWORDS,
    SEASON_KEYWORDS,
    TIME_OF_DAY_KEYWORDS,
    WEATHER_KEYWORDS,
)
from app.domain.chat_context import ChatModeContext
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


MONTH_TO_SEASON: dict[str, tuple[str, ...]] = {
    "spring": ("march", "april", "may", "\u043c\u0430\u0440\u0442", "\u0430\u043f\u0440\u0435\u043b", "\u043c\u0430\u0439"),
    "summer": ("june", "july", "august", "\u0438\u044e\u043d", "\u0438\u044e\u043b", "\u0430\u0432\u0433\u0443\u0441\u0442"),
    "autumn": (
        "september",
        "october",
        "november",
        "fall",
        "\u0441\u0435\u043d\u0442\u044f\u0431\u0440",
        "\u043e\u043a\u0442\u044f\u0431\u0440",
        "\u043d\u043e\u044f\u0431\u0440",
        "\u043e\u0441\u0435\u043d\u044c\u044e",
    ),
    "winter": (
        "december",
        "january",
        "february",
        "\u0434\u0435\u043a\u0430\u0431\u0440",
        "\u044f\u043d\u0432\u0430\u0440",
        "\u0444\u0435\u0432\u0440\u0430\u043b",
        "\u0437\u0438\u043c\u043e\u0439",
    ),
}


class OccasionExtractionService(OccasionContextExtractor):
    def __init__(self, *, reasoner: LLMReasoner | None = None) -> None:
        self.reasoner = reasoner

    async def extract(
        self,
        *,
        locale: str,
        user_message: str,
        context: ChatModeContext,
        existing_context: OccasionContext | None,
        asset_metadata: dict[str, Any] | None = None,
        fallback_history: list[dict[str, str]] | None = None,
    ) -> OccasionContext:
        occasion_context = existing_context.model_copy(deep=True) if existing_context is not None else OccasionContext()
        occasion_context.append_raw_text(user_message)
        extraction_confidence = 0.0

        if self.reasoner is not None:
            try:
                extraction = await self.reasoner.extract_occasion_slots(
                    locale=locale,
                    user_message=user_message,
                    conversation_history=self._build_history(
                        context=context,
                        fallback_history=fallback_history or [],
                    ),
                    existing_slots={
                        "event_type": occasion_context.event_type,
                        "venue": occasion_context.location,
                        "dress_code": occasion_context.dress_code,
                        "time_of_day": occasion_context.time_of_day,
                        "season_or_weather": occasion_context.weather_context or occasion_context.season,
                        "desired_impression": occasion_context.desired_impression,
                    },
                )
                occasion_context.event_type = extraction.event_type or occasion_context.event_type
                occasion_context.location = extraction.venue or occasion_context.location
                occasion_context.time_of_day = extraction.time_of_day or occasion_context.time_of_day
                if extraction.season_or_weather:
                    season_or_weather = extraction.season_or_weather.lower()
                    occasion_context.season = (
                        self.first_keyword_match(season_or_weather, SEASON_KEYWORDS)
                        or self.infer_season_from_calendar_context(season_or_weather)
                        or occasion_context.season
                    )
                    occasion_context.weather_context = extraction.season_or_weather
                occasion_context.dress_code = extraction.dress_code or occasion_context.dress_code
                occasion_context.desired_impression = extraction.desired_impression or occasion_context.desired_impression
                extraction_confidence = 0.6
            except LLMReasonerError:
                extraction_confidence = 0.0

        lowered = user_message.lower()
        occasion_context.event_type = occasion_context.event_type or self.first_keyword_match(lowered, EVENT_TYPE_KEYWORDS)
        occasion_context.location = occasion_context.location or self.first_keyword_match(lowered, LOCATION_KEYWORDS)
        occasion_context.time_of_day = occasion_context.time_of_day or self.first_keyword_match(lowered, TIME_OF_DAY_KEYWORDS)
        occasion_context.season = (
            occasion_context.season
            or self.first_keyword_match(lowered, SEASON_KEYWORDS)
            or self.infer_season_from_calendar_context(lowered)
        )
        occasion_context.dress_code = occasion_context.dress_code or self.first_keyword_match(lowered, DRESS_CODE_KEYWORDS)
        occasion_context.desired_impression = (
            occasion_context.desired_impression or self.first_keyword_match(lowered, IMPRESSION_KEYWORDS)
        )
        occasion_context.weather_context = (
            occasion_context.weather_context or self.first_keyword_match(lowered, WEATHER_KEYWORDS)
        )

        self._merge_detected_preferences(occasion_context=occasion_context, lowered=lowered)
        if asset_metadata:
            original_filename = asset_metadata.get("original_filename")
            if isinstance(original_filename, str) and original_filename.strip():
                occasion_context.append_raw_text(original_filename.strip())

        scalar_slots = [
            occasion_context.event_type,
            occasion_context.location,
            occasion_context.time_of_day,
            occasion_context.season,
            occasion_context.dress_code,
            occasion_context.weather_context,
            occasion_context.desired_impression,
        ]
        filled_scalar_slots = sum(1 for value in scalar_slots if value)
        total_slots = len(scalar_slots)
        heuristic_confidence = min(filled_scalar_slots / total_slots if total_slots else 0.0, 1.0)
        occasion_context.confidence = max(extraction_confidence, heuristic_confidence)
        return occasion_context

    def first_keyword_match(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> str | None:
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints):
                return canonical
        return None

    def infer_season_from_calendar_context(self, lowered_text: str) -> str | None:
        return self.first_keyword_match(lowered_text, MONTH_TO_SEASON)

    def _merge_detected_preferences(self, *, occasion_context: OccasionContext, lowered: str) -> None:
        for color in self._find_all_matches(lowered, COLOR_KEYWORDS):
            if color not in occasion_context.color_preferences:
                occasion_context.color_preferences.append(color)
        for garment in self._find_all_matches(lowered, GARMENT_KEYWORDS):
            if garment not in occasion_context.garment_preferences:
                occasion_context.garment_preferences.append(garment)

        constraint_markers = (
            ("\u0431\u0435\u0437 \u043a\u0430\u0431\u043b\u0443\u043a", "avoid heels"),
            ("\u0431\u0435\u0437 \u0433\u0430\u043b\u0441\u0442\u0443\u043a\u0430", "avoid tie"),
            ("no heels", "avoid heels"),
            ("no tie", "avoid tie"),
        )
        for marker, normalized in constraint_markers:
            if marker in lowered and normalized not in occasion_context.constraints:
                occasion_context.constraints.append(normalized)

        comfort_markers = (
            ("\u0443\u0434\u043e\u0431", "comfort-first"),
            ("\u043a\u043e\u043c\u0444\u043e\u0440\u0442", "comfort-first"),
            ("comfortable", "comfort-first"),
            ("warm enough", "warm layers"),
            ("\u043d\u0435 \u0436\u0430\u0440\u043a\u043e", "breathable"),
        )
        for marker, normalized in comfort_markers:
            if marker in lowered and normalized not in occasion_context.comfort_requirements:
                occasion_context.comfort_requirements.append(normalized)

    def _find_all_matches(self, lowered_text: str, mapping: dict[str, tuple[str, ...]]) -> list[str]:
        matches: list[str] = []
        for canonical, hints in mapping.items():
            if any(hint in lowered_text for hint in hints) and canonical not in matches:
                matches.append(canonical)
        return matches

    def _build_history(
        self,
        *,
        context: ChatModeContext,
        fallback_history: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        if context.conversation_memory:
            return [
                {"role": item.role, "content": item.content.strip()[:280]}
                for item in context.conversation_memory[-6:]
                if item.content.strip()
            ]
        history: list[dict[str, str]] = []
        for message in fallback_history[-6:]:
            content = message.get("content", "") if isinstance(message, dict) else ""
            if not content.strip():
                continue
            role = message.get("role", "user") if isinstance(message, dict) else "user"
            if role not in {"user", "assistant", "system"}:
                role = "user"
            history.append({"role": role, "content": content.strip()[:280]})
        return history
