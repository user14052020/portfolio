from pydantic import BaseModel, Field


class VisualPreset(BaseModel):
    id: str
    name: str
    mode_affinity: list[str] = Field(default_factory=list)
    background_family: str | None = None
    layout_archetype: str | None = None
    spacing_density: str | None = None
    object_count_range: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    anchor_garment_centrality: str | None = None
    practical_coherence: str | None = None
    diversity_bias: str | None = None
    tags: list[str] = Field(default_factory=list)
