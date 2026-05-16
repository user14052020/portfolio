from typing import Any

from app.domain.style_exploration.entities.style_selection_profile import StyleSelectionProfile


class StyleSelectionProfileContextMapper:
    _WEARABILITY_TO_COMFORT = {
        "wearable": ["high_comfort"],
        "balanced": ["balanced"],
        "expressive": ["style_first"],
    }
    _SILHOUETTE_TO_PROFILE = {
        "relaxed": {
            "fit_preferences": ["relaxed"],
            "silhouette_preferences": ["soft"],
        },
        "tailored": {
            "fit_preferences": ["fitted"],
            "silhouette_preferences": ["structured"],
        },
        "oversized": {
            "fit_preferences": ["oversized"],
            "silhouette_preferences": ["voluminous_top"],
        },
        "fluid": {
            "fit_preferences": ["relaxed"],
            "silhouette_preferences": ["soft"],
        },
    }
    _PALETTE_TO_COLOR = {
        "neutral": ["neutral palette"],
        "dark": ["dark palette"],
        "colorful": ["saturated color", "colorful palette"],
        "soft": ["soft palette"],
    }
    _MOOD_TO_STYLE_TERMS = {
        "minimal": ["minimal"],
        "romantic": ["romantic"],
        "street": ["street"],
        "classic": ["classic"],
        "artful": ["artful"],
    }

    def map_payload(self, value: Any) -> dict[str, Any] | None:
        return self.map_profile(StyleSelectionProfile.from_payload(value))

    def map_profile(self, profile: StyleSelectionProfile | None) -> dict[str, Any] | None:
        if profile is None or not profile.has_signal():
            return None

        update: dict[str, Any] = {
            "style_selection_profile": profile.model_dump(mode="json", exclude_none=True),
            "style_preferences": self._style_preferences(profile),
            "source": "style_exploration_questionnaire",
        }

        if profile.presentation_profile:
            update["presentation_profile"] = profile.presentation_profile
        if profile.wearability:
            update["comfort_preferences"] = list(self._WEARABILITY_TO_COMFORT[profile.wearability])
            update["style_wearability_preference"] = profile.wearability
        if profile.silhouette:
            update.update(
                {
                    key: list(values)
                    for key, values in self._SILHOUETTE_TO_PROFILE[profile.silhouette].items()
                }
            )
            update["style_silhouette_preference"] = profile.silhouette
        if profile.palette:
            update["color_preferences"] = list(self._PALETTE_TO_COLOR[profile.palette])
            update["style_palette_preference"] = profile.palette
        if profile.mood:
            update["style_mood_preferences"] = list(self._MOOD_TO_STYLE_TERMS[profile.mood])
            update["style_mood_preference"] = profile.mood

        return {key: value for key, value in update.items() if value}

    def _style_preferences(self, profile: StyleSelectionProfile) -> list[str]:
        preferences: list[str] = []
        for value in (
            profile.wearability,
            profile.silhouette,
            profile.palette,
            profile.mood,
        ):
            if value and value not in preferences:
                preferences.append(value)
        if profile.mood:
            for term in self._MOOD_TO_STYLE_TERMS[profile.mood]:
                if term not in preferences:
                    preferences.append(term)
        return preferences
