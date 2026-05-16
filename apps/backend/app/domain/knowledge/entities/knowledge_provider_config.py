from pydantic import BaseModel, Field


class KnowledgeProviderConfig(BaseModel):
    code: str
    name: str
    provider_type: str = "runtime"
    description: str | None = None
    is_enabled: bool = True
    is_runtime_enabled: bool = True
    is_ingestion_enabled: bool = False
    priority: int = 100
    runtime_roles: list[str] = Field(default_factory=list)

    def is_available_for_runtime(self) -> bool:
        return self.is_enabled and self.is_runtime_enabled

    def is_available_for_ingestion(self) -> bool:
        return self.is_enabled and self.is_ingestion_enabled
