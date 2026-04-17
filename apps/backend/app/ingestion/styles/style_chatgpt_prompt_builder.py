from __future__ import annotations

import json
from typing import Any


STYLE_ENRICHMENT_PROMPT_VERSION = "style-enrichment-chatgpt-2026-04-17.v1"
STYLE_ENRICHMENT_SCHEMA_VERSION = "style-enrichment-schema.v1"
STYLE_ENRICHMENT_FACET_VERSION = "v1"


def build_style_enrichment_system_prompt() -> str:
    return (
        "You enrich a fashion style knowledge base from stored source text. "
        "Return strict JSON only, no markdown, no commentary. "
        "Do not invent facts that are not reasonably supported by the source text. "
        "If a field is missing or weakly supported, return an empty list or null text. "
        "Prefer short concrete phrases. "
        "Lists must contain only strings. "
        "Return this exact top-level shape: "
        "{"
        '"knowledge": {'
        '"style_name": string|null, '
        '"core_definition": string|null, '
        '"core_style_logic": string[], '
        '"styling_rules": string[], '
        '"casual_adaptations": string[], '
        '"statement_pieces": string[], '
        '"status_markers": string[], '
        '"overlap_context": string[], '
        '"historical_notes": string[], '
        '"negative_guidance": string[]'
        "}, "
        '"visual_language": {'
        '"palette": string[], '
        '"lighting_mood": string[], '
        '"photo_treatment": string[], '
        '"visual_motifs": string[], '
        '"patterns_textures": string[], '
        '"platform_visual_cues": string[]'
        "}, "
        '"fashion_items": {'
        '"tops": string[], '
        '"bottoms": string[], '
        '"shoes": string[], '
        '"accessories": string[], '
        '"hair_makeup": string[], '
        '"signature_details": string[]'
        "}, "
        '"image_prompt_atoms": {'
        '"hero_garments": string[], '
        '"secondary_garments": string[], '
        '"core_accessories": string[], '
        '"props": string[], '
        '"materials": string[], '
        '"composition_cues": string[], '
        '"negative_constraints": string[], '
        '"visual_motifs": string[], '
        '"lighting_mood": string[], '
        '"photo_treatment": string[]'
        "}, "
        '"relations": {'
        '"related_styles": string[], '
        '"overlap_styles": string[], '
        '"preceded_by": string[], '
        '"succeeded_by": string[], '
        '"brands": string[], '
        '"platforms": string[], '
        '"origin_regions": string[], '
        '"era": string[]'
        "}, "
        '"presentation": {'
        '"short_explanation": string|null, '
        '"one_sentence_description": string|null, '
        '"what_makes_it_distinct": string[]'
        "}"
        "}. "
        "Keep the output aligned with the source style text only."
    )


def build_style_enrichment_user_prompt(
    *,
    style_id: int,
    style_slug: str,
    style_name: str,
    source_title: str | None,
    source_url: str | None,
    source_payload: str,
    evidence_items: list[str],
) -> str:
    request_payload: dict[str, Any] = {
        "task": "Enrich one fashion style into typed JSON blocks for consultation and image generation runtime.",
        "prompt_version": STYLE_ENRICHMENT_PROMPT_VERSION,
        "schema_version": STYLE_ENRICHMENT_SCHEMA_VERSION,
        "style": {
            "style_id": style_id,
            "style_slug": style_slug,
            "style_name": style_name,
            "source_title": source_title,
            "source_url": source_url,
        },
        "instructions": [
            "Use only the supplied source text and evidence snippets.",
            "Keep phrasing concise and operational.",
            "Do not repeat near-duplicate strings across lists.",
            "If a value is not grounded, leave it empty.",
        ],
        "source_text": source_payload,
        "evidence_snippets": evidence_items,
    }
    return json.dumps(request_payload, ensure_ascii=False)
