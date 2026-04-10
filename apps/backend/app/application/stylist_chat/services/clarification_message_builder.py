from app.domain.chat_context import AnchorGarment, OccasionContext
from app.domain.chat_modes import ClarificationKind


class ClarificationMessageBuilder:
    def garment_entry_prompt(self, locale: str) -> str:
        return (
            "Опиши вещь, вокруг которой нужно собрать образ: что это за предмет, какого он цвета, из какого материала и как сидит."
            if locale == "ru"
            else "Describe the garment you want to build the outfit around: what it is, the color, the material, and the fit."
        )

    def garment_clarification_prompt(self, locale: str, anchor: AnchorGarment) -> str:
        if not anchor.garment_type:
            return (
                "Уточни, пожалуйста, что это за вещь: рубашка, жакет, платье, брюки, обувь или что-то другое."
                if locale == "ru"
                else "Please clarify what kind of garment it is: a shirt, jacket, dress, trousers, shoes, or something else."
            )
        return (
            "Добавь один-два признака вещи: цвет, материал или посадку. Этого достаточно, чтобы собрать цельный образ."
            if locale == "ru"
            else "Add one or two garment details such as the color, material, or fit. That is enough for me to build a coherent look."
        )

    def occasion_entry_prompt(self, locale: str) -> str:
        return (
            "Расскажи, пожалуйста, что это за событие, в какое время суток оно проходит, какой сейчас сезон и есть ли dress code или желаемое впечатление."
            if locale == "ru"
            else "Tell me what kind of event it is, what time of day it happens, what season it is, and whether there is a dress code or a desired impression."
        )

    def occasion_clarification(
        self,
        locale: str,
        occasion_context: OccasionContext,
    ) -> tuple[ClarificationKind | None, str | None]:
        missing = occasion_context.missing_core_slots()
        if not missing:
            return None, None
        if "event_type" in missing:
            return (
                ClarificationKind.OCCASION_EVENT_TYPE,
                (
                    "Что это за событие: свадьба, свидание, ужин, театр, вечеринка или что-то другое?"
                    if locale == "ru"
                    else "What kind of event is it: a wedding, date, dinner, theater night, party, or something else?"
                ),
            )
        if "time_of_day" in missing:
            return (
                ClarificationKind.OCCASION_TIME_OF_DAY,
                (
                    "В какое время суток это событие: утром, днём или вечером?"
                    if locale == "ru"
                    else "What time of day is the event: morning, daytime, or evening?"
                ),
            )
        if "season" in missing:
            return (
                ClarificationKind.OCCASION_SEASON,
                (
                    "Какой сейчас сезон для этого события: весна, лето, осень или зима?"
                    if locale == "ru"
                    else "What season is it for this event: spring, summer, autumn, or winter?"
                ),
            )
        if "dress_code" in missing and "desired_impression" in missing:
            return (
                ClarificationKind.OCCASION_DRESS_CODE,
                (
                    "Есть ли dress code или образ, который ты хочешь производить: более элегантный, расслабленный, заметный?"
                    if locale == "ru"
                    else "Is there a dress code or a specific impression you want to create, such as elegant, relaxed, or striking?"
                ),
            )
        return (
            ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS,
            (
                "Мне нужно ещё немного контекста: событие, время суток, сезон и хотя бы dress code или желаемое впечатление."
                if locale == "ru"
                else "I still need a bit more context: the event type, the time of day, the season, and at least a dress code or a desired impression."
            ),
        )
