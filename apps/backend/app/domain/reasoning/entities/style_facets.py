from typing import Any

from pydantic import BaseModel, Field, computed_field, model_validator


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
    advice_facets: list[StyleAdviceFacet] = Field(default_factory=list)
    image_facets: list[StyleImageFacet] = Field(default_factory=list)
    visual_language_facets: list[StyleVisualLanguageFacet] = Field(default_factory=list)
    relation_facets: list[StyleRelationFacet] = Field(default_factory=list)
    profile_context_present: bool = False
    alignment_notes: list[str] = Field(default_factory=list)
    filtered_out: list[str] = Field(default_factory=list)
    boosted_facet_categories: list[str] = Field(default_factory=list)
    removed_item_types: list[str] = Field(default_factory=list)
    facet_weights: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _expand_legacy_facets(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "facets" not in data:
            return data

        raw = dict(data)
        bundle = raw.pop("facets")
        if isinstance(bundle, StyleFacetBundle):
            raw.setdefault("advice_facets", list(bundle.advice_facets))
            raw.setdefault("image_facets", list(bundle.image_facets))
            raw.setdefault("visual_language_facets", list(bundle.visual_language_facets))
            raw.setdefault("relation_facets", list(bundle.relation_facets))
            return raw
        if isinstance(bundle, dict):
            raw.setdefault("advice_facets", list(bundle.get("advice_facets", [])))
            raw.setdefault("image_facets", list(bundle.get("image_facets", [])))
            raw.setdefault(
                "visual_language_facets",
                list(bundle.get("visual_language_facets", [])),
            )
            raw.setdefault("relation_facets", list(bundle.get("relation_facets", [])))
        return raw

    @computed_field(return_type=StyleFacetBundle)
    @property
    def facets(self) -> StyleFacetBundle:
        return StyleFacetBundle(
            advice_facets=list(self.advice_facets),
            image_facets=list(self.image_facets),
            visual_language_facets=list(self.visual_language_facets),
            relation_facets=list(self.relation_facets),
        )

    def total_count(self) -> int:
        return self.facets.total_count()
