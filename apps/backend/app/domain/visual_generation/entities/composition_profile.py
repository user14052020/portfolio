from pydantic import BaseModel


class CompositionProfile(BaseModel):
    layout_archetype: str | None = None
    background_family: str | None = None
    object_count_range: str | None = None
    spacing_density: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    anchor_garment_centrality: str | None = None
    practical_coherence: str | None = None
