from enum import Enum


class OccasionSlot(str, Enum):
    EVENT_TYPE = "event_type"
    LOCATION = "location"
    TIME_OF_DAY = "time_of_day"
    SEASON = "season"
    DRESS_CODE = "dress_code"
    WEATHER_CONTEXT = "weather_context"
    DESIRED_IMPRESSION = "desired_impression"
    CONSTRAINTS = "constraints"
    COLOR_PREFERENCES = "color_preferences"
    GARMENT_PREFERENCES = "garment_preferences"
    COMFORT_REQUIREMENTS = "comfort_requirements"
