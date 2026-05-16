from pydantic import BaseModel, Field

from app.domain.knowledge.entities import KnowledgeRuntimeFlags


DEFAULT_KNOWLEDGE_PROVIDER_PRIORITIES: dict[str, int] = {
    "style_ingestion": 10,
    "malevich": 20,
    "fashion_historian": 40,
    "stylist": 50,
    "stylist_editorial": 50,
}

MAX_KNOWLEDGE_PROVIDER_PRIORITY = 1000


class KnowledgeRuntimeSettings(BaseModel):
    style_ingestion_enabled: bool = True
    malevich_enabled: bool = False
    fashion_historian_enabled: bool = False
    stylist_enabled: bool = False
    use_editorial_knowledge: bool = False
    use_historical_context: bool = True
    use_color_poetics: bool = True
    provider_priorities: dict[str, int] = Field(
        default_factory=lambda: dict(DEFAULT_KNOWLEDGE_PROVIDER_PRIORITIES)
    )

    def runtime_flags(self) -> KnowledgeRuntimeFlags:
        return KnowledgeRuntimeFlags(
            style_ingestion_enabled=self.style_ingestion_enabled,
            malevich_enabled=self.malevich_enabled,
            fashion_historian_enabled=self.fashion_historian_enabled,
            stylist_enabled=self.stylist_enabled,
            use_editorial_knowledge=self.use_editorial_knowledge,
            use_historical_context=self.use_historical_context,
            use_color_poetics=self.use_color_poetics,
        )

    def normalized_provider_priorities(self) -> dict[str, int]:
        priorities = dict(DEFAULT_KNOWLEDGE_PROVIDER_PRIORITIES)
        for code, raw_value in self.provider_priorities.items():
            normalized_code = str(code).strip().lower()
            if not normalized_code:
                continue
            try:
                priorities[normalized_code] = int(raw_value)
            except (TypeError, ValueError):
                continue
        return priorities
