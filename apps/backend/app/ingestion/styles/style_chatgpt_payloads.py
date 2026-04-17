from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    return " ".join(cleaned.split())


def _clean_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        raw_items = [value]

    result: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = _clean_text(item)
        if cleaned is None:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


class _EnrichmentPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StyleKnowledgePayload(_EnrichmentPayloadModel):
    style_name: str | None = None
    core_definition: str | None = None
    core_style_logic: list[str] = Field(default_factory=list)
    styling_rules: list[str] = Field(default_factory=list)
    casual_adaptations: list[str] = Field(default_factory=list)
    statement_pieces: list[str] = Field(default_factory=list)
    status_markers: list[str] = Field(default_factory=list)
    overlap_context: list[str] = Field(default_factory=list)
    historical_notes: list[str] = Field(default_factory=list)
    negative_guidance: list[str] = Field(default_factory=list)

    @field_validator("style_name", "core_definition", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return _clean_text(value)

    @field_validator(
        "core_style_logic",
        "styling_rules",
        "casual_adaptations",
        "statement_pieces",
        "status_markers",
        "overlap_context",
        "historical_notes",
        "negative_guidance",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StyleVisualLanguagePayload(_EnrichmentPayloadModel):
    palette: list[str] = Field(default_factory=list)
    lighting_mood: list[str] = Field(default_factory=list)
    photo_treatment: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)
    patterns_textures: list[str] = Field(default_factory=list)
    platform_visual_cues: list[str] = Field(default_factory=list)

    @field_validator(
        "palette",
        "lighting_mood",
        "photo_treatment",
        "visual_motifs",
        "patterns_textures",
        "platform_visual_cues",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StyleFashionItemsPayload(_EnrichmentPayloadModel):
    tops: list[str] = Field(default_factory=list)
    bottoms: list[str] = Field(default_factory=list)
    shoes: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    hair_makeup: list[str] = Field(default_factory=list)
    signature_details: list[str] = Field(default_factory=list)

    @field_validator(
        "tops",
        "bottoms",
        "shoes",
        "accessories",
        "hair_makeup",
        "signature_details",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StyleImagePayload(_EnrichmentPayloadModel):
    hero_garments: list[str] = Field(default_factory=list)
    secondary_garments: list[str] = Field(default_factory=list)
    core_accessories: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    composition_cues: list[str] = Field(default_factory=list)
    negative_constraints: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)
    lighting_mood: list[str] = Field(default_factory=list)
    photo_treatment: list[str] = Field(default_factory=list)

    @field_validator(
        "hero_garments",
        "secondary_garments",
        "core_accessories",
        "props",
        "materials",
        "composition_cues",
        "negative_constraints",
        "visual_motifs",
        "lighting_mood",
        "photo_treatment",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StyleRelationsPayload(_EnrichmentPayloadModel):
    related_styles: list[str] = Field(default_factory=list)
    overlap_styles: list[str] = Field(default_factory=list)
    preceded_by: list[str] = Field(default_factory=list)
    succeeded_by: list[str] = Field(default_factory=list)
    brands: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    origin_regions: list[str] = Field(default_factory=list)
    era: list[str] = Field(default_factory=list)

    @field_validator(
        "related_styles",
        "overlap_styles",
        "preceded_by",
        "succeeded_by",
        "brands",
        "platforms",
        "origin_regions",
        "era",
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StylePresentationPayload(_EnrichmentPayloadModel):
    short_explanation: str | None = None
    one_sentence_description: str | None = None
    what_makes_it_distinct: list[str] = Field(default_factory=list)

    @field_validator("short_explanation", "one_sentence_description", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: Any) -> str | None:
        return _clean_text(value)

    @field_validator("what_makes_it_distinct", mode="before")
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _clean_string_list(value)


class StyleEnrichmentPayload(_EnrichmentPayloadModel):
    knowledge: StyleKnowledgePayload
    visual_language: StyleVisualLanguagePayload
    fashion_items: StyleFashionItemsPayload
    image_prompt_atoms: StyleImagePayload
    relations: StyleRelationsPayload
    presentation: StylePresentationPayload
