from __future__ import annotations

import re
from dataclasses import dataclass

from app.application.knowledge.contracts import KnowledgeProvider
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeProviderConfig, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


@dataclass(frozen=True, slots=True)
class ColorTheoryEntry:
    key: str
    markers: tuple[str, ...]
    title: dict[str, str]
    summary: dict[str, str]
    body: dict[str, str]
    tags: tuple[str, ...]
    confidence: float = 0.82

    def localized_title(self, locale: str) -> str:
        return self.title.get(locale) or self.title["en"]

    def localized_summary(self, locale: str) -> str:
        return self.summary.get(locale) or self.summary["en"]

    def localized_body(self, locale: str) -> str:
        return self.body.get(locale) or self.body["en"]


class CuratedColorTheoryKnowledgeProvider(KnowledgeProvider):
    """Provider-backed color knowledge for free-form stylist conversation."""

    def __init__(
        self,
        *,
        entries: tuple[ColorTheoryEntry, ...] | None = None,
        config: KnowledgeProviderConfig | None = None,
    ) -> None:
        self._entries = entries or DEFAULT_COLOR_THEORY_ENTRIES
        self.config = config or KnowledgeProviderConfig(
            code="color_theory",
            name="Color Theory",
            provider_type="curated_color_theory",
            is_enabled=True,
            is_runtime_enabled=True,
            is_ingestion_enabled=False,
            priority=30,
            runtime_roles=["reasoning", "voice", "color_poetics"],
        )

    async def search(self, *, query: KnowledgeQuery) -> list[KnowledgeCard]:
        locale = "ru" if query.locale == "ru" else "en"
        search_text = self._search_text(query)
        if not search_text:
            return []

        cards: list[KnowledgeCard] = []
        for entry in self._entries:
            score = self._match_score(entry=entry, search_text=search_text)
            if score <= 0:
                continue
            cards.append(
                KnowledgeCard(
                    id=f"color_theory:{entry.key}:{locale}",
                    knowledge_type=KnowledgeType.COLOR_THEORY,
                    provider_code=self.config.code,
                    provider_priority=self.config.priority,
                    title=entry.localized_title(locale),
                    summary=entry.localized_summary(locale),
                    body=entry.localized_body(locale),
                    tone_role="color_poetics",
                    tags=list(entry.tags),
                    confidence=min(entry.confidence + score * 0.04, 0.98),
                    freshness="curated",
                    metadata={
                        "color_family": entry.key,
                        "matched_markers_count": score,
                    },
                )
            )
        return cards

    def _search_text(self, query: KnowledgeQuery) -> str:
        current = self._normalize(query.resolved_user_request())
        context = self._normalize(query.conversation_context)
        profile_terms = self._normalize(" ".join(self._profile_color_terms(query)))
        if self._should_use_conversation_context(current):
            return " ".join(part for part in (current, context, profile_terms) if part)
        return " ".join(part for part in (current, profile_terms) if part)

    def _profile_color_terms(self, query: KnowledgeQuery) -> list[str]:
        values: list[str] = []
        profile = query.profile_context or {}
        for key in ("color_preferences", "color_avoidances", "preferred_colors", "palette"):
            raw_value = profile.get(key)
            if isinstance(raw_value, str):
                values.append(raw_value)
            elif isinstance(raw_value, list):
                values.extend(str(item) for item in raw_value)
        anchor = query.anchor_garment or {}
        for key in ("color_primary", "color", "material"):
            raw_value = anchor.get(key)
            if isinstance(raw_value, str):
                values.append(raw_value)
        return values

    def _match_score(self, *, entry: ColorTheoryEntry, search_text: str) -> int:
        return sum(1 for marker in entry.markers if self._contains_marker(search_text, marker))

    def _contains_marker(self, text: str, marker: str) -> bool:
        normalized_marker = self._normalize(marker)
        if not normalized_marker:
            return False
        if " " in normalized_marker or "-" in normalized_marker:
            return normalized_marker in text
        return re.search(rf"(?<!\w){re.escape(normalized_marker)}(?!\w)", text) is not None

    def _should_use_conversation_context(self, current: str) -> bool:
        if not current:
            return False
        words = current.split()
        if len(words) > 3:
            return False
        return current in _ACTION_ONLY_MARKERS or any(current.startswith(marker) for marker in _ACTION_ONLY_MARKERS)

    def _normalize(self, value: str | None) -> str:
        return " ".join((value or "").strip().lower().replace("ё", "е").split())


_ACTION_ONLY_MARKERS = {
    "делай",
    "сделай",
    "давай",
    "ок",
    "окей",
    "хорошо",
    "продолжай",
    "do it",
    "go ahead",
    "continue",
    "ok",
    "okay",
    "yes",
}


DEFAULT_COLOR_THEORY_ENTRIES: tuple[ColorTheoryEntry, ...] = (
    ColorTheoryEntry(
        key="blue",
        markers=(
            "blue",
            "navy",
            "cobalt",
            "sky blue",
            "dark blue",
            "синий",
            "синего",
            "синем",
            "синим",
            "синюю",
            "синие",
            "синих",
            "голубой",
            "голубого",
            "голубом",
            "голубым",
            "темно-синий",
            "тёмно-синий",
        ),
        title={
            "en": "Blue in styling",
            "ru": "Синий в стилизации",
        },
        summary={
            "en": (
                "Blue works as a calm wardrobe anchor: softer than black, "
                "but still structured and composed."
            ),
            "ru": (
                "Синий в одежде работает как спокойная опора: он мягче черного, "
                "но все еще выглядит собранно."
            ),
        },
        body={
            "en": (
                "Navy suits business, evening, and smart casual settings; pale blue lightens "
                "the outfit; cobalt is strongest as an accent. Reliable pairings include white, "
                "ivory, grey, beige, brown, burgundy, and denim in a different depth. For a more "
                "expensive effect, keep textures matte and substantial: wool, cotton, denim, "
                "suede, or smooth leather. To keep blue from feeling flat, vary shade depth and "
                "add one warm contrast through shoes, a belt, a bag, or jewelry."
            ),
            "ru": (
                "Темно-синий подходит для делового, вечернего и smart casual контекста; "
                "голубой облегчает образ; кобальт лучше использовать как акцент. Надежные "
                "пары: белый, молочный, серый, бежевый, коричневый, бордовый и деним другой "
                "насыщенности. Для более дорогого эффекта держи фактуры матовыми и плотными: "
                "шерсть, хлопок, деним, замша или гладкая кожа. Чтобы синий не стал скучным, "
                "меняй глубину оттенков и добавляй один теплый контраст через обувь, ремень, "
                "сумку или украшение."
            ),
        },
        tags=("blue", "navy", "cobalt", "синий", "голубой", "color_pairing"),
    ),
)
