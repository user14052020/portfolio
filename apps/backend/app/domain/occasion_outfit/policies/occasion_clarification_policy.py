from app.domain.chat_modes import ClarificationKind
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.enums.occasion_slot import OccasionSlot
from app.domain.occasion_outfit.policies.occasion_completeness_policy import OccasionCompletenessAssessment


class OccasionClarificationPolicy:
    def build(
        self,
        *,
        locale: str,
        context: OccasionContext,
        assessment: OccasionCompletenessAssessment,
    ) -> tuple[ClarificationKind, str]:
        slot = assessment.clarification_slot
        if slot == OccasionSlot.EVENT_TYPE:
            return (
                ClarificationKind.OCCASION_EVENT_TYPE,
                (
                    "Что это за событие: свадьба, выставка, ужин, театр, вечеринка или что-то другое?"
                    if locale == "ru"
                    else "What kind of event is it: a wedding, exhibition, dinner, theater night, party, or something else?"
                ),
            )
        if slot == OccasionSlot.TIME_OF_DAY:
            return (
                ClarificationKind.OCCASION_TIME_OF_DAY,
                (
                    "В какое время это событие: утром, днём или вечером?"
                    if locale == "ru"
                    else "What time of day is it: morning, daytime, or evening?"
                ),
            )
        if slot == OccasionSlot.SEASON:
            return (
                ClarificationKind.OCCASION_SEASON,
                (
                    "Какой сейчас сезон для этого события: весна, лето, осень или зима?"
                    if locale == "ru"
                    else "What season is it for this event: spring, summer, autumn, or winter?"
                ),
            )
        if slot == OccasionSlot.DRESS_CODE:
            event_hint = context.event_type or ("событие" if locale == "ru" else "event")
            return (
                ClarificationKind.OCCASION_DRESS_CODE,
                (
                    f"Есть ли dress code для {event_hint}, или какое впечатление вы хотите произвести: элегантно, расслабленно, смело?"
                    if locale == "ru"
                    else f"Is there a dress code for the {event_hint}, or what impression do you want to create: elegant, relaxed, or bold?"
                ),
            )
        return (
            ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS,
            (
                "Мне нужен ещё контекст по событию: тип события, время суток, сезон и хотя бы dress code или желаемое впечатление."
                if locale == "ru"
                else "I still need more event context: the event type, time of day, season, and at least a dress code or desired impression."
            ),
        )
