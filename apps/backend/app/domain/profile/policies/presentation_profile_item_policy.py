import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal


PresentationItemCategory = Literal["garment", "footwear", "accessory", "prop", "item", "text"]


@dataclass(frozen=True)
class PresentationItemReplacement:
    category: str
    original: str
    replacement: str | None
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class PresentationItemSanitizationResult:
    items: list[str]
    replacements: list[PresentationItemReplacement]
    removed: list[PresentationItemReplacement]

    @property
    def changed(self) -> bool:
        return bool(self.replacements or self.removed)


@dataclass(frozen=True)
class _PresentationItemRule:
    blocked_terms: tuple[str, ...]


class PresentationProfileItemPolicy:
    """Keeps generated outfit items compatible with explicit presentation profile."""

    _MASCULINE_RULES: Mapping[str, tuple[_PresentationItemRule, ...]] = {
        "garment": (
            _PresentationItemRule(
                (
                    "skirt",
                    "mini skirt",
                    "midi skirt",
                    "maxi skirt",
                    "skort",
                    "dress",
                    "slip dress",
                    "sundress",
                    "gown",
                    "blouse",
                    "chiffon blouse",
                    "camisole",
                    "corset",
                    "bodice",
                    "bustier",
                    "bralette",
                    "bra top",
                    "crop top",
                )
            ),
        ),
        "footwear": (
            _PresentationItemRule(
                (
                    "heel",
                    "heels",
                    "heeled",
                    "high heel",
                    "high heels",
                    "stiletto",
                    "stilettos",
                    "pump",
                    "pumps",
                    "slingback",
                    "slingbacks",
                    "mary jane",
                    "mary janes",
                    "ballet flat",
                    "ballet flats",
                )
            ),
        ),
        "accessory": (
            _PresentationItemRule(
                (
                    "handbag",
                    "purse",
                    "clutch",
                    "mini bag",
                    "micro bag",
                    "pearl bag",
                    "pearl handbag",
                    "headband",
                    "hair clip",
                    "barrette",
                    "bow",
                    "ribbon",
                    "pearls",
                    "pearl necklace",
                )
            ),
        ),
        "prop": (
            _PresentationItemRule(
                (
                    "handbag",
                    "purse",
                    "clutch",
                    "pearl bag",
                    "bow",
                    "headband",
                    "hair clip",
                )
            ),
        ),
    }
    _RULES_BY_PROFILE: Mapping[str, Mapping[str, tuple[_PresentationItemRule, ...]]] = {
        "masculine": _MASCULINE_RULES,
    }
    _NEGATIVE_CONSTRAINTS: Mapping[str, tuple[str, ...]] = {
        "masculine": (
            "masculine presentation only: no skirts, dresses, gowns, heels, pumps, "
            "stilettos, handbags, clutches, bows, headbands, pearl bags, "
            "or feminine-coded accessories",
        ),
    }
    _COLOR_TERMS = (
        "dark navy",
        "light gray",
        "light grey",
        "charcoal gray",
        "charcoal grey",
        "navy",
        "black",
        "white",
        "ivory",
        "cream",
        "beige",
        "camel",
        "brown",
        "tan",
        "khaki",
        "olive",
        "green",
        "blue",
        "cobalt",
        "red",
        "burgundy",
        "pink",
        "purple",
        "yellow",
        "gray",
        "grey",
        "charcoal",
        "silver",
        "gold",
        "metallic",
    )

    def sanitize_items(
        self,
        *,
        presentation_profile: str | None,
        category: PresentationItemCategory,
        items: Iterable[str],
    ) -> PresentationItemSanitizationResult:
        profile = self._normalize_profile(presentation_profile)
        sanitized: list[str] = []
        replacements: list[PresentationItemReplacement] = []
        removed: list[PresentationItemReplacement] = []

        for item in items:
            cleaned = self._clean(item)
            if not cleaned:
                continue
            matched_terms = self.incompatible_terms(
                presentation_profile=profile,
                category=category,
                text=cleaned,
            )
            if not matched_terms:
                self._append_unique(sanitized, cleaned)
                continue

            replacement = self._replacement_for(
                presentation_profile=profile,
                category=category,
                original=cleaned,
                matched_terms=matched_terms,
            )
            record = PresentationItemReplacement(
                category=category,
                original=cleaned,
                replacement=replacement,
                matched_terms=matched_terms,
            )
            if replacement:
                self._append_unique(sanitized, replacement)
                replacements.append(record)
            else:
                removed.append(record)

        return PresentationItemSanitizationResult(
            items=sanitized,
            replacements=replacements,
            removed=removed,
        )

    def filter_texts(
        self,
        *,
        presentation_profile: str | None,
        items: Iterable[str],
    ) -> PresentationItemSanitizationResult:
        profile = self._normalize_profile(presentation_profile)
        kept: list[str] = []
        removed: list[PresentationItemReplacement] = []
        for item in items:
            cleaned = self._clean(item)
            if not cleaned:
                continue
            matched_terms = self.incompatible_terms(
                presentation_profile=profile,
                category="text",
                text=cleaned,
            )
            if matched_terms:
                removed.append(
                    PresentationItemReplacement(
                        category="text",
                        original=cleaned,
                        replacement=None,
                        matched_terms=matched_terms,
                    )
                )
                continue
            self._append_unique(kept, cleaned)
        return PresentationItemSanitizationResult(items=kept, replacements=[], removed=removed)

    def incompatible_item_count(
        self,
        *,
        presentation_profile: str | None,
        items_by_category: Mapping[PresentationItemCategory, Iterable[str]],
    ) -> int:
        profile = self._normalize_profile(presentation_profile)
        if profile not in self._RULES_BY_PROFILE:
            return 0
        count = 0
        for category, items in items_by_category.items():
            for item in items:
                if self.incompatible_terms(
                    presentation_profile=profile,
                    category=category,
                    text=str(item),
                ):
                    count += 1
        return count

    def incompatible_terms(
        self,
        *,
        presentation_profile: str | None,
        category: PresentationItemCategory,
        text: str,
    ) -> tuple[str, ...]:
        profile = self._normalize_profile(presentation_profile)
        if profile not in self._RULES_BY_PROFILE:
            return ()
        normalized_text = self._normalize_text(text)
        if not normalized_text:
            return ()
        matched: list[str] = []
        for rule in self._rules_for(profile=profile, category=category):
            for term in rule.blocked_terms:
                if self._contains_term(normalized_text, term):
                    self._append_unique(matched, self._normalize_text(term))
        return tuple(matched)

    def negative_constraints(self, presentation_profile: str | None) -> list[str]:
        profile = self._normalize_profile(presentation_profile)
        return list(self._NEGATIVE_CONSTRAINTS.get(profile, ()))

    def _rules_for(
        self,
        *,
        profile: str,
        category: PresentationItemCategory,
    ) -> tuple[_PresentationItemRule, ...]:
        profile_rules = self._RULES_BY_PROFILE.get(profile, {})
        if category == "item" or category == "text":
            return tuple(
                rule
                for field in ("garment", "footwear", "accessory", "prop")
                for rule in profile_rules.get(field, ())
            )
        if category == "prop":
            return tuple((*profile_rules.get("prop", ()), *profile_rules.get("accessory", ())))
        return tuple(profile_rules.get(category, ()))

    def _replacement_for(
        self,
        *,
        presentation_profile: str,
        category: PresentationItemCategory,
        original: str,
        matched_terms: tuple[str, ...],
    ) -> str | None:
        if presentation_profile != "masculine":
            return None

        normalized = self._normalize_text(original)
        term_set = set(matched_terms)
        replacement: str | None = None
        if category in {"garment", "item"}:
            if {"blouse", "chiffon blouse", "camisole"} & term_set:
                replacement = "crisp shirt"
            elif {"corset", "bodice", "bustier", "bralette", "bra top", "crop top"} & term_set:
                replacement = "structured vest"
            elif {"dress", "slip dress", "sundress", "gown"} & term_set:
                replacement = "tailored suit separates"
            elif {"skirt", "mini skirt", "midi skirt", "maxi skirt", "skort"} & term_set:
                if "cargo" in normalized:
                    replacement = "structured cargo trousers"
                elif "pleated" in normalized:
                    replacement = "pleated tailored trousers"
                else:
                    replacement = "tailored trousers"
        if category in {"footwear", "item"} and replacement is None:
            if {
                "heel",
                "heels",
                "heeled",
                "high heel",
                "high heels",
                "stiletto",
                "stilettos",
                "pump",
                "pumps",
                "slingback",
                "slingbacks",
                "mary jane",
                "mary janes",
                "ballet flat",
                "ballet flats",
            } & term_set:
                replacement = "leather loafers"
        if category in {"accessory", "prop", "item"} and replacement is None:
            if {
                "handbag",
                "purse",
                "clutch",
                "mini bag",
                "micro bag",
                "pearl bag",
                "pearl handbag",
            } & term_set:
                replacement = "structured leather crossbody bag"
            elif {
                "headband",
                "hair clip",
                "barrette",
                "bow",
                "ribbon",
                "pearls",
                "pearl necklace",
            } & term_set:
                replacement = "minimal metal watch"

        if replacement is None:
            return None
        return self._preserve_color(original=original, replacement=replacement)

    def _preserve_color(self, *, original: str, replacement: str) -> str:
        normalized_original = self._normalize_text(original)
        normalized_replacement = self._normalize_text(replacement)
        for color in self._COLOR_TERMS:
            if self._contains_term(normalized_original, color) and not self._contains_term(
                normalized_replacement,
                color,
            ):
                return f"{color} {replacement}"
        return replacement

    def _normalize_profile(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = self._normalize_text(value)
        aliases = {
            "male": "masculine",
            "man": "masculine",
            "menswear": "masculine",
            "female": "feminine",
            "woman": "feminine",
            "womenswear": "feminine",
            "universal": "unisex",
            "neutral": "unisex",
        }
        return aliases.get(normalized, normalized)

    def _contains_term(self, normalized_text: str, term: str) -> bool:
        normalized_term = self._normalize_text(term)
        if not normalized_term:
            return False
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(normalized_term).replace(r"\ ", r"\s+")
            + r"(?![a-z0-9])"
        )
        return re.search(pattern, normalized_text) is not None

    def _normalize_text(self, value: str) -> str:
        lowered = str(value or "").lower()
        no_separators = re.sub(r"[-_/]+", " ", lowered)
        no_punctuation = re.sub(r"[^a-z0-9\s]+", " ", no_separators)
        return " ".join(no_punctuation.split())

    def _clean(self, value: object) -> str:
        return str(value or "").strip()

    def _append_unique(self, values: list[str], value: str) -> None:
        key = self._normalize_text(value)
        if not key:
            return
        if all(self._normalize_text(existing) != key for existing in values):
            values.append(value)
