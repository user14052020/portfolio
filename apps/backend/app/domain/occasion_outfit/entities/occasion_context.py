from pydantic import BaseModel, Field

from app.domain.occasion_outfit.enums.occasion_slot import OccasionSlot


class OccasionContext(BaseModel):
    raw_user_texts: list[str] = Field(default_factory=list)
    event_type: str | None = None
    location: str | None = None
    time_of_day: str | None = None
    season: str | None = None
    dress_code: str | None = None
    weather_context: str | None = None
    desired_impression: str | None = None
    constraints: list[str] = Field(default_factory=list)
    color_preferences: list[str] = Field(default_factory=list)
    garment_preferences: list[str] = Field(default_factory=list)
    comfort_requirements: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False

    def append_raw_text(self, text: str) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        if cleaned not in self.raw_user_texts:
            self.raw_user_texts.append(cleaned)
        self.raw_user_texts = self.raw_user_texts[-6:]

    def filled_slots(self) -> list[str]:
        slots: list[str] = []
        for slot in OccasionSlot:
            value = self.slot_value(slot)
            if isinstance(value, list):
                if value:
                    slots.append(slot.value)
                continue
            if value:
                slots.append(slot.value)
        return slots

    def missing_core_slots(self) -> list[str]:
        missing: list[str] = []
        if not self.event_type:
            missing.append(OccasionSlot.EVENT_TYPE.value)
        if not self.time_of_day:
            missing.append(OccasionSlot.TIME_OF_DAY.value)
        if not self.season:
            missing.append(OccasionSlot.SEASON.value)
        if not self.dress_code and not self.desired_impression:
            missing.extend([OccasionSlot.DRESS_CODE.value, OccasionSlot.DESIRED_IMPRESSION.value])
        return missing

    def slot_value(self, slot: OccasionSlot) -> str | list[str] | None:
        mapping: dict[OccasionSlot, str | list[str] | None] = {
            OccasionSlot.EVENT_TYPE: self.event_type,
            OccasionSlot.LOCATION: self.location,
            OccasionSlot.TIME_OF_DAY: self.time_of_day,
            OccasionSlot.SEASON: self.season,
            OccasionSlot.DRESS_CODE: self.dress_code,
            OccasionSlot.WEATHER_CONTEXT: self.weather_context,
            OccasionSlot.DESIRED_IMPRESSION: self.desired_impression,
            OccasionSlot.CONSTRAINTS: self.constraints,
            OccasionSlot.COLOR_PREFERENCES: self.color_preferences,
            OccasionSlot.GARMENT_PREFERENCES: self.garment_preferences,
            OccasionSlot.COMFORT_REQUIREMENTS: self.comfort_requirements,
        }
        return mapping[slot]
