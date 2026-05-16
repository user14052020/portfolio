from typing import Any, Literal

from pydantic import BaseModel


StyleWearability = Literal["wearable", "balanced", "expressive"]
StylePresentationProfile = Literal["feminine", "masculine", "androgynous", "unisex"]
StyleSilhouettePreference = Literal["relaxed", "tailored", "oversized", "fluid"]
StylePalettePreference = Literal["neutral", "dark", "colorful", "soft"]
StyleMoodPreference = Literal["minimal", "romantic", "street", "classic", "artful"]


class StyleSelectionProfile(BaseModel):
    presentation_profile: StylePresentationProfile | None = None
    wearability: StyleWearability | None = None
    silhouette: StyleSilhouettePreference | None = None
    palette: StylePalettePreference | None = None
    mood: StyleMoodPreference | None = None

    @classmethod
    def from_payload(cls, value: Any) -> "StyleSelectionProfile | None":
        if not isinstance(value, dict):
            return None
        try:
            profile = cls.model_validate(value)
        except Exception:
            return None
        return profile if profile.has_signal() else None

    def has_signal(self) -> bool:
        return any((
            self.presentation_profile,
            self.wearability,
            self.silhouette,
            self.palette,
            self.mood,
        ))
