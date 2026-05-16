from pydantic import BaseModel, Field

from app.domain.knowledge_runtime_settings import MAX_KNOWLEDGE_PROVIDER_PRIORITY
from app.schemas.common import TimestampedRead


class KnowledgeRuntimeSettingsUpdate(BaseModel):
    style_ingestion_enabled: bool
    malevich_enabled: bool
    fashion_historian_enabled: bool
    stylist_enabled: bool
    use_editorial_knowledge: bool
    use_historical_context: bool
    use_color_poetics: bool
    provider_priorities: dict[str, int] = Field(default_factory=dict)


class KnowledgeRuntimeSettingsRead(TimestampedRead):
    id: int
    style_ingestion_enabled: bool
    malevich_enabled: bool
    fashion_historian_enabled: bool
    stylist_enabled: bool
    use_editorial_knowledge: bool
    use_historical_context: bool
    use_color_poetics: bool
    provider_priorities: dict[str, int] = Field(default_factory=dict)


class KnowledgeRuntimeDiagnosticsRead(BaseModel):
    runtime_flags: dict[str, bool]
    provider_priorities: dict[str, int]
    enabled_runtime_providers: list[dict[str, object]] = Field(default_factory=list)

    @staticmethod
    def validate_priorities(priorities: dict[str, int]) -> dict[str, int]:
        return {
            code: max(0, min(int(priority), MAX_KNOWLEDGE_PROVIDER_PRIORITY))
            for code, priority in priorities.items()
        }
