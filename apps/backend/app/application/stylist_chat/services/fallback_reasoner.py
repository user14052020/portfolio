from app.application.stylist_chat.contracts.ports import FallbackReasonerStrategy, ReasoningOutput


class DeterministicFallbackReasoner(FallbackReasonerStrategy):
    async def decide(self, *, locale: str, reasoning_input: dict[str, object]) -> ReasoningOutput:
        mode = str(reasoning_input.get("session_intent") or "general_advice")
        if mode == "garment_matching":
            reply_text = (
                "Собрала базовую идею образа вокруг вещи и запускаю визуализацию."
                if locale == "ru"
                else "I assembled a grounded look around the garment and will visualize it."
            )
            image_brief = "editorial flat lay outfit built around the anchor garment with balanced layers and clean styling"
            route = "text_and_generation"
        elif mode == "occasion_outfit":
            reply_text = (
                "Собрала понятный образ под событие и запускаю генерацию."
                if locale == "ru"
                else "I shaped a clear occasion-ready outfit and will generate it now."
            )
            image_brief = "occasion-ready editorial flat lay outfit with polished layers and event-appropriate styling"
            route = "text_and_generation"
        elif mode == "style_exploration":
            reply_text = (
                "Нашла новое стилевое направление и запускаю визуализацию."
                if locale == "ru"
                else "I found a fresh style direction and will visualize it."
            )
            image_brief = "fresh editorial flat lay outfit with a distinct style direction and varied silhouette"
            route = "text_and_generation"
        else:
            reply_text = (
                "Дам короткую практичную рекомендацию и при необходимости можем углубить её следующим сообщением."
                if locale == "ru"
                else "I can offer a short practical recommendation, and we can deepen it in the next message."
            )
            image_brief = ""
            route = "text_only"
        return ReasoningOutput(
            reply_text=reply_text,
            image_brief_en=image_brief,
            route=route,
            provider="deterministic-fallback",
            reasoning_mode="fallback",
        )
