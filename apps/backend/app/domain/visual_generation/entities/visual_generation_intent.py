from pydantic import BaseModel, Field


class VisualGenerationIntent(BaseModel):
    mode: str
    priority: str | None = None
    anti_repeat_constraints: dict[str, object] = Field(default_factory=dict)
    knowledge_refs: list[dict[str, object]] = Field(default_factory=list)
