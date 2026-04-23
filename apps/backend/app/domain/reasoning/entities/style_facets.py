from pydantic import BaseModel, Field


class StyleAdviceFacet(BaseModel):
    style_id: int
    core_style_logic: list[str] = Field(default_factory=list)
    styling_rules: list[str] = Field(default_factory=list)
    casual_adaptations: list[str] = Field(default_factory=list)
    statement_pieces: list[str] = Field(default_factory=list)
    status_markers: list[str] = Field(default_factory=list)
    overlap_context: list[str] = Field(default_factory=list)
    historical_notes: list[str] = Field(default_factory=list)
    negative_guidance: list[str] = Field(default_factory=list)


class StyleImageFacet(BaseModel):
    style_id: int
    hero_garments: list[str] = Field(default_factory=list)
    secondary_garments: list[str] = Field(default_factory=list)
    core_accessories: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    composition_cues: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)


class StyleVisualLanguageFacet(BaseModel):
    style_id: int
    palette: list[str] = Field(default_factory=list)
    lighting_mood: list[str] = Field(default_factory=list)
    photo_treatment: list[str] = Field(default_factory=list)
    mood_keywords: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)
    platform_visual_cues: list[str] = Field(default_factory=list)


class StyleRelationFacet(BaseModel):
    style_id: int
    related_styles: list[str] = Field(default_factory=list)
    overlap_styles: list[str] = Field(default_factory=list)
    historical_relations: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)


class StyleFacetBundle(BaseModel):
    advice_facets: list[StyleAdviceFacet] = Field(default_factory=list)
    image_facets: list[StyleImageFacet] = Field(default_factory=list)
    visual_language_facets: list[StyleVisualLanguageFacet] = Field(default_factory=list)
    relation_facets: list[StyleRelationFacet] = Field(default_factory=list)

    def total_count(self) -> int:
        return (
            len(self.advice_facets)
            + len(self.image_facets)
            + len(self.visual_language_facets)
            + len(self.relation_facets)
        )

    def is_empty(self) -> bool:
        return self.total_count() == 0


class ProfileAlignedStyleFacetBundle(BaseModel):
    facets: StyleFacetBundle = Field(default_factory=StyleFacetBundle)
    profile_context_present: bool = False
    alignment_notes: list[str] = Field(default_factory=list)
    filtered_out: list[str] = Field(default_factory=list)
    facet_weights: dict[str, float] = Field(default_factory=dict)
