from typing import Any

from app.domain.profile.policies.presentation_profile_item_policy import (
    PresentationItemSanitizationResult,
    PresentationProfileItemPolicy,
)
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class ProfilePresentationBriefSanitizer:
    """Applies explicit presentation-profile item constraints before prompt rendering."""

    _ITEM_FIELDS = (
        ("hero_garments", "garment"),
        ("secondary_garments", "garment"),
        ("garment_list", "garment"),
        ("footwear", "footwear"),
        ("accessories", "accessory"),
        ("props", "prop"),
    )
    _TEXT_FIELDS = (
        "tailoring_logic",
        "color_logic",
        "styling_notes",
        "composition_rules",
        "photo_treatment",
    )

    def __init__(
        self,
        *,
        item_policy: PresentationProfileItemPolicy | None = None,
    ) -> None:
        self.item_policy = item_policy or PresentationProfileItemPolicy()

    def sanitize(self, brief: FashionBrief) -> FashionBrief:
        presentation_profile = self._presentation_profile(brief)
        if not presentation_profile:
            return brief

        updates: dict[str, Any] = {}
        sanitized_fields: list[str] = []
        replacements: list[dict[str, Any]] = []
        removed: list[dict[str, Any]] = []

        for field_name, category in self._ITEM_FIELDS:
            result = self.item_policy.sanitize_items(
                presentation_profile=presentation_profile,
                category=category,
                items=getattr(brief, field_name),
            )
            if result.changed:
                updates[field_name] = result.items
                sanitized_fields.append(field_name)
                replacements.extend(self._replacement_records(result))
                removed.extend(self._removed_records(result))

        for field_name in self._TEXT_FIELDS:
            result = self.item_policy.filter_texts(
                presentation_profile=presentation_profile,
                items=getattr(brief, field_name),
            )
            if result.changed:
                updates[field_name] = result.items
                sanitized_fields.append(field_name)
                removed.extend(self._removed_records(result))

        negative_constraints = self._unique(
            [
                *brief.negative_constraints,
                *self.item_policy.negative_constraints(presentation_profile),
            ]
        )
        if negative_constraints != brief.negative_constraints:
            updates["negative_constraints"] = negative_constraints

        if not updates:
            return brief

        updates["metadata"] = {
            **brief.metadata,
            "presentation_profile_item_policy": {
                "profile": presentation_profile,
                "sanitized_fields": sanitized_fields,
                "replacements": replacements,
                "removed": removed,
            },
        }
        return brief.model_copy(update=updates, deep=True)

    def _presentation_profile(self, brief: FashionBrief) -> str | None:
        constraints = (
            brief.profile_constraints
            if isinstance(brief.profile_constraints, dict)
            else {}
        )
        raw = constraints.get("presentation_profile") or constraints.get("gender")
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip().lower()
        aliases = {
            "male": "masculine",
            "man": "masculine",
            "female": "feminine",
            "woman": "feminine",
            "universal": "unisex",
            "neutral": "unisex",
        }
        return aliases.get(cleaned, cleaned)

    def _replacement_records(
        self,
        result: PresentationItemSanitizationResult,
    ) -> list[dict[str, Any]]:
        return [
            {
                "category": item.category,
                "original": item.original,
                "replacement": item.replacement,
                "matched_terms": list(item.matched_terms),
            }
            for item in result.replacements
        ]

    def _removed_records(
        self,
        result: PresentationItemSanitizationResult,
    ) -> list[dict[str, Any]]:
        return [
            {
                "category": item.category,
                "original": item.original,
                "matched_terms": list(item.matched_terms),
            }
            for item in result.removed
        ]

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = str(value or "").strip()
            key = " ".join(cleaned.lower().split())
            if not cleaned or key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result
