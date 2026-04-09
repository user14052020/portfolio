from __future__ import annotations

import re
from dataclasses import dataclass

from slugify import slugify

from app.ingestion.styles.contracts import (
    EnrichedStyleDocument,
    NormalizedLink,
    NormalizedSection,
    NormalizedStyleDocument,
    StyleRelationSeed,
    TaxonomyLinkSeed,
    TraitSeed,
)
from app.ingestion.styles.style_feature_catalog import FEATURE_VOCABULARIES


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WHITESPACE_RE = re.compile(r"\s+")

CULTURAL_CONTEXT_TERMS = (
    "music",
    "interior",
    "design",
    "architecture",
    "art",
    "film",
    "cinema",
    "literature",
    "subculture",
    "culture",
)
HISTORICAL_CONTEXT_TERMS = (
    "history",
    "historical",
    "origin",
    "originated",
    "emerged",
    "era",
    "century",
    "revival",
)
VISUAL_CONTEXT_TERMS = (
    "look",
    "appearance",
    "visual",
    "silhouette",
    "palette",
    "texture",
    "garment",
    "outfit",
)
PALETTE_RELATION_TERMS = ("color", "colour", "palette", "hue", "hues")
SILHOUETTE_RELATION_TERMS = ("silhouette", "shape", "cut", "fit", "tailoring", "tailored")
NEGATIVE_TERMS = (
    "avoid",
    "without",
    "not",
    "never",
    "rather than",
    "instead of",
)
STYLING_TERMS = (
    "wear",
    "pair",
    "style",
    "combine",
    "layer",
    "styled",
)
RELATED_SECTION_TERMS = ("related", "see also", "similar", "adjacent", "variants", "substyles", "family")
FAMILY_SECTION_TERMS = ("family", "substyles", "variants", "types", "subcategories")
CATEGORY_SECTION_TERMS = ("category", "categories", "subculture", "aesthetic family", "umbrella")
COLOR_SECTION_TERMS = ("color", "colour", "palette")
ERA_SECTION_TERMS = ("era", "decade", "history", "historical", "origins", "background")
REGION_SECTION_TERMS = ("region", "origins", "origin", "culture", "cultural")
NON_STYLE_LINK_PREFIXES = (
    "category:",
    "template:",
    "user:",
    "special:",
    "help:",
    "file:",
    "forum:",
    "blog:",
)
NON_STYLE_LINK_TITLES = {
    "list of aesthetics",
    "aesthetics wiki",
    "main page",
    "fashion",
    "music",
    "art",
    "film",
    "cinema",
    "literature",
    "interior design",
    "architecture",
    "culture",
    "history",
    "color",
    "colour",
    "format and content",
    "aesthetics wiki:what pages are allowed/removed",
}
RELATION_NAVIGATION_MARKERS = (
    "article guide",
    "music genres",
    "what pages are allowed",
    "examples of",
    "example of",
    "timeline",
    "preceded by",
    "succeeded by",
)
MAX_RELATION_SEEDS_PER_STYLE = 8
MAX_RELATION_SEEDS_BY_TYPE: dict[str, int] = {
    "adjacent_to": 4,
    "shares_palette_with": 2,
    "shares_silhouette_with": 2,
}
MAX_RELATION_SEEDS_PER_REASON_BY_TYPE: dict[str, int] = {
    "fusion_candidate": 2,
}
RELATION_PHRASE_RULES: tuple[tuple[tuple[str, ...], str, float], ...] = (
    (("inspired by", "influence from", "influenced by", "based on", "derived from"), "inspired_by", 0.92),
    (("subcategory of", "substyle of", "subgenre of", "type of", "branch of"), "subcategory_of", 0.95),
    (("same family", "same aesthetic family", "shares the same family"), "same_family", 0.88),
    (("historically related", "revival of", "historical predecessor", "descended from"), "historically_related", 0.84),
    (("contrast", "counterpart", "opposite"), "contrast_pair", 0.8),
    (("fusion", "blend of", "mix of"), "fusion_candidate", 0.82),
    (("similar to", "related to", "close to"), "adjacent_to", 0.72),
)
VOCABULARY_BY_TYPE = {vocabulary.trait_type: vocabulary for vocabulary in FEATURE_VOCABULARIES}
LINK_TAXONOMY_MAPPING: dict[str, tuple[str, str, float]] = {
    "family_hint": ("family", "subculture", 0.92),
    "category_hint": ("category", "subculture", 0.9),
    "color_hint": ("color", "color", 0.92),
    "decade_hint": ("decade", "era", 0.9),
    "region_hint": ("region", "region", 0.9),
    "umbrella_hint": ("umbrella_term", "subculture", 0.9),
    "taxonomy_hint": ("category", "subculture", 0.82),
}
TRAIT_SECTION_HINTS: dict[str, tuple[str, ...]] = {
    "color": COLOR_SECTION_TERMS,
    "material": ("fabric", "fabrics", "material", "materials", "texture", "textures"),
    "silhouette": ("silhouette", "shape", "cut", "fit"),
    "garment": ("fashion", "clothing", "garments", "wardrobe", "apparel"),
    "footwear": ("footwear", "shoes", "shoe"),
    "accessory": ("accessories", "accessory", "details"),
    "motif": ("patterns", "pattern", "textures", "motif"),
    "era": ERA_SECTION_TERMS,
    "region": REGION_SECTION_TERMS,
    "subculture": ("subculture", "culture", "family", "category"),
    "art_reference": ("art", "visual art", "design", "reference", "references"),
    "mood": ("mood", "vibe", "atmosphere"),
    "occasion": ("occasion", "wear", "events", "event"),
    "seasonality": ("season", "seasons", "weather"),
    "hair_makeup": ("hair", "makeup", "beauty"),
    "composition_hint": ("styling", "composition", "outfit logic", "visual composition"),
}


@dataclass(frozen=True)
class ExtractedSemanticBundle:
    profile_payload: dict[str, object]
    trait_seeds: tuple[TraitSeed, ...]
    taxonomy_link_seeds: tuple[TaxonomyLinkSeed, ...]
    relation_seeds: tuple[StyleRelationSeed, ...]


@dataclass(frozen=True)
class TraitEvidenceMatch:
    evidence_text: str
    weight: float


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return WHITESPACE_RE.sub(" ", value).strip()


def _split_sentences(value: str) -> tuple[str, ...]:
    cleaned = _clean_text(value)
    if not cleaned:
        return ()
    return tuple(sentence.strip() for sentence in SENTENCE_SPLIT_RE.split(cleaned) if sentence.strip())


def _contains_keyword(text: str | None, keyword: str) -> bool:
    cleaned = _clean_text(text)
    if not cleaned:
        return False
    return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", cleaned, flags=re.IGNORECASE) is not None


def _contains_any_keyword(text: str | None, keywords: tuple[str, ...]) -> bool:
    return any(_contains_keyword(text, keyword) for keyword in keywords)


def _first_non_empty_section(sections: tuple[NormalizedSection, ...]) -> str | None:
    for section in sections:
        text = _clean_text(section.section_text)
        if text:
            return text
    return None


def _select_context_sentence(
    sections: tuple[NormalizedSection, ...],
    *,
    title_terms: tuple[str, ...] = (),
    body_terms: tuple[str, ...] = (),
) -> str | None:
    lowered_title_terms = tuple(item.casefold() for item in title_terms)
    lowered_body_terms = tuple(item.casefold() for item in body_terms)

    for section in sections:
        title = _clean_text(section.section_title).casefold()
        if lowered_title_terms and any(term in title for term in lowered_title_terms):
            sentences = _split_sentences(section.section_text)
            if sentences:
                return sentences[0]

    for section in sections:
        for sentence in _split_sentences(section.section_text):
            lowered = sentence.casefold()
            if any(term in lowered for term in lowered_body_terms):
                return sentence
    return None


def _collect_supporting_sentences(
    sections: tuple[NormalizedSection, ...],
    *,
    search_terms: tuple[str, ...],
    limit: int = 5,
) -> tuple[str, ...]:
    results: list[str] = []
    lowered_terms = tuple(term.casefold() for term in search_terms)
    for section in sections:
        for sentence in _split_sentences(section.section_text):
            lowered = sentence.casefold()
            if any(term in lowered for term in lowered_terms):
                if sentence not in results:
                    results.append(sentence)
                if len(results) >= limit:
                    return tuple(results)
    return tuple(results)


class StyleFeatureExtractor:
    def extract(self, normalized: NormalizedStyleDocument) -> ExtractedSemanticBundle:
        canonical_text = _clean_text(normalized.raw_text)
        sections = normalized.sections
        links = normalized.links

        essence = _select_context_sentence(
            sections,
            title_terms=("overview", "description", "fashion"),
            body_terms=("style", "aesthetic", "fashion"),
        ) or _first_non_empty_section(sections) or canonical_text
        essence = _truncate(essence, 280)

        fashion_summary = _select_context_sentence(
            sections,
            title_terms=("fashion", "appearance", "style"),
            body_terms=("garment", "outfit", "clothing", "wear"),
        ) or essence
        visual_summary = _select_context_sentence(
            sections,
            title_terms=("visual", "appearance"),
            body_terms=VISUAL_CONTEXT_TERMS,
        )
        historical_context = _select_context_sentence(
            sections,
            title_terms=("history", "origins", "background"),
            body_terms=HISTORICAL_CONTEXT_TERMS,
        )
        cultural_context = _select_context_sentence(
            sections,
            title_terms=("culture", "media", "music", "art"),
            body_terms=CULTURAL_CONTEXT_TERMS,
        )

        trait_seeds = self._extract_traits(sections)
        grouped_values = self._group_trait_values(trait_seeds)

        negative_constraints = _collect_supporting_sentences(sections, search_terms=NEGATIVE_TERMS, limit=4)
        styling_advice = _collect_supporting_sentences(sections, search_terms=STYLING_TERMS, limit=4)
        image_prompt_notes = self._build_image_prompt_notes(grouped_values)
        taxonomy_link_seeds = self._dedupe_taxonomy_seeds(
            (
                *self._build_taxonomy_seeds(grouped_values),
                *self._build_section_taxonomy_seeds(sections),
                *self._build_link_taxonomy_seeds(links),
            )
        )
        relation_seeds = self._build_relation_seeds(
            source_title=normalized.source_title,
            source_slug=normalized.source_url.rsplit("/", 1)[-1],
            sections=sections,
            links=links,
        )

        profile_payload = {
            "essence": essence,
            "fashion_summary": fashion_summary,
            "visual_summary": visual_summary,
            "historical_context": historical_context,
            "cultural_context": cultural_context,
            "mood_keywords_json": list(grouped_values.get("mood", ())),
            "color_palette_json": list(grouped_values.get("color", ())),
            "materials_json": list(grouped_values.get("material", ())),
            "silhouettes_json": list(grouped_values.get("silhouette", ())),
            "garments_json": list(grouped_values.get("garment", ())),
            "footwear_json": list(grouped_values.get("footwear", ())),
            "accessories_json": list(grouped_values.get("accessory", ())),
            "hair_makeup_json": list(grouped_values.get("hair_makeup", ())),
            "patterns_textures_json": list(grouped_values.get("motif", ())),
            "seasonality_json": list(grouped_values.get("seasonality", ())),
            "occasion_fit_json": list(grouped_values.get("occasion", ())),
            "negative_constraints_json": list(negative_constraints),
            "styling_advice_json": list(styling_advice),
            "image_prompt_notes_json": list(image_prompt_notes),
        }

        return ExtractedSemanticBundle(
            profile_payload=profile_payload,
            trait_seeds=trait_seeds,
            taxonomy_link_seeds=taxonomy_link_seeds,
            relation_seeds=relation_seeds,
        )

    def _extract_traits(self, sections: tuple[NormalizedSection, ...]) -> tuple[TraitSeed, ...]:
        results: list[TraitSeed] = []
        seen: set[tuple[str, str]] = set()

        for vocabulary in FEATURE_VOCABULARIES:
            for canonical_value, keywords in vocabulary.values.items():
                trait_match = self._find_trait_match(
                    sections,
                    trait_type=vocabulary.trait_type,
                    keywords=keywords,
                )
                if trait_match is None:
                    continue
                signature = (vocabulary.trait_type, canonical_value)
                if signature in seen:
                    continue
                seen.add(signature)
                results.append(
                    TraitSeed(
                        trait_type=vocabulary.trait_type,
                        trait_value=canonical_value,
                        weight=trait_match.weight,
                        evidence_kind="section_sentence",
                        evidence_text=trait_match.evidence_text,
                    )
                )

        return tuple(results)

    def _find_trait_match(
        self,
        sections: tuple[NormalizedSection, ...],
        *,
        trait_type: str,
        keywords: tuple[str, ...],
    ) -> TraitEvidenceMatch | None:
        lowered_keywords = tuple(item.casefold() for item in keywords)
        evidence_text: str | None = None
        match_count = 0
        section_title_boost = 0.0

        for section in sections:
            section_title = _clean_text(section.section_title).casefold()
            for sentence in _split_sentences(section.section_text):
                lowered = sentence.casefold()
                if any(keyword in lowered for keyword in lowered_keywords):
                    match_count += 1
                    if evidence_text is None:
                        evidence_text = sentence
                    if self._section_title_matches_trait(trait_type=trait_type, section_title=section_title):
                        section_title_boost = max(section_title_boost, 0.12)

        if evidence_text is None:
            return None

        weight = 0.58 + min(0.24, (match_count - 1) * 0.08) + section_title_boost
        return TraitEvidenceMatch(
            weight=round(min(weight, 1.0), 4),
            evidence_text=evidence_text,
        )

    def _section_title_matches_trait(
        self,
        *,
        trait_type: str,
        section_title: str,
    ) -> bool:
        if not section_title:
            return False
        hints = TRAIT_SECTION_HINTS.get(trait_type, ())
        return any(hint in section_title for hint in hints)

    def _group_trait_values(self, traits: tuple[TraitSeed, ...]) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for trait in traits:
            bucket = grouped.setdefault(trait.trait_type, [])
            if trait.trait_value not in bucket:
                bucket.append(trait.trait_value)
        return {key: tuple(values) for key, values in grouped.items()}

    def _build_taxonomy_seeds(
        self,
        grouped_values: dict[str, tuple[str, ...]],
    ) -> tuple[TaxonomyLinkSeed, ...]:
        seeds: list[TaxonomyLinkSeed] = []

        for color in grouped_values.get("color", ()):
            seeds.append(
                TaxonomyLinkSeed(
                    taxonomy_type="color",
                    name=color,
                    slug=slugify(color),
                    description=None,
                    link_strength=0.9,
                    evidence_kind="derived_trait_group",
                    evidence_text=color,
                )
            )

        for era in grouped_values.get("era", ()):
            seeds.append(
                TaxonomyLinkSeed(
                    taxonomy_type="decade",
                    name=era,
                    slug=slugify(era),
                    description=None,
                    link_strength=0.85,
                    evidence_kind="derived_trait_group",
                    evidence_text=era,
                )
            )

        for region in grouped_values.get("region", ()):
            seeds.append(
                TaxonomyLinkSeed(
                    taxonomy_type="region",
                    name=region,
                    slug=slugify(region),
                    description=None,
                    link_strength=0.85,
                    evidence_kind="derived_trait_group",
                    evidence_text=region,
                )
            )

        for subculture in grouped_values.get("subculture", ()):
            seeds.append(
                TaxonomyLinkSeed(
                    taxonomy_type="category",
                    name=subculture,
                    slug=slugify(subculture),
                    description=None,
                    link_strength=0.75,
                    evidence_kind="derived_trait_group",
                    evidence_text=subculture,
                )
            )

        deduped: dict[tuple[str, str], TaxonomyLinkSeed] = {}
        for seed in seeds:
            deduped[(seed.taxonomy_type, seed.slug)] = seed
        return tuple(deduped.values())

    def _build_section_taxonomy_seeds(
        self,
        sections: tuple[NormalizedSection, ...],
    ) -> tuple[TaxonomyLinkSeed, ...]:
        seeds: list[TaxonomyLinkSeed] = []

        for section in sections:
            title = _clean_text(section.section_title).casefold()
            if not title:
                continue

            if any(term in title for term in COLOR_SECTION_TERMS):
                seeds.extend(self._taxonomy_seeds_from_text(section.section_text, taxonomy_type="color", trait_type="color"))
            if any(term in title for term in ERA_SECTION_TERMS):
                seeds.extend(self._taxonomy_seeds_from_text(section.section_text, taxonomy_type="decade", trait_type="era"))
            if any(term in title for term in REGION_SECTION_TERMS):
                seeds.extend(self._taxonomy_seeds_from_text(section.section_text, taxonomy_type="region", trait_type="region"))
            if any(term in title for term in CATEGORY_SECTION_TERMS):
                seeds.extend(self._taxonomy_seeds_from_text(section.section_text, taxonomy_type="category", trait_type="subculture"))
            if any(term in title for term in FAMILY_SECTION_TERMS):
                seeds.extend(
                    self._taxonomy_seeds_from_text(
                        section.section_text,
                        taxonomy_type="umbrella_term",
                        trait_type="subculture",
                    )
                )

        return tuple(seeds)

    def _build_link_taxonomy_seeds(
        self,
        links: tuple[NormalizedLink, ...],
    ) -> tuple[TaxonomyLinkSeed, ...]:
        seeds: list[TaxonomyLinkSeed] = []
        for link in links:
            if link.link_type not in set(LINK_TAXONOMY_MAPPING):
                continue
            target_title = _clean_text(link.target_title or link.anchor_text)
            if not target_title:
                continue
            taxonomy_type, trait_type, link_strength = LINK_TAXONOMY_MAPPING[link.link_type]
            matched_from_vocab = self._taxonomy_seeds_from_text(
                target_title,
                taxonomy_type=taxonomy_type,
                trait_type=trait_type,
                evidence_kind=link.link_type,
                link_strength=link_strength,
            )
            if matched_from_vocab:
                seeds.extend(matched_from_vocab)
                continue

            if taxonomy_type in {"family", "category", "umbrella_term"}:
                seeds.append(
                    TaxonomyLinkSeed(
                        taxonomy_type=taxonomy_type,
                        name=target_title,
                        slug=slugify(target_title),
                        description=None,
                        link_strength=link_strength,
                        evidence_kind=link.link_type,
                        evidence_text=target_title,
                    )
                )
        return tuple(seeds)

    def _taxonomy_seeds_from_text(
        self,
        text: str,
        *,
        taxonomy_type: str,
        trait_type: str,
        evidence_kind: str = "section_sentence",
        link_strength: float = 0.8,
    ) -> tuple[TaxonomyLinkSeed, ...]:
        vocabulary = VOCABULARY_BY_TYPE[trait_type]
        matched_values = self._match_vocabulary_values(text, vocabulary=vocabulary)
        if not matched_values:
            return ()
        evidence_text = _truncate(text, 240) or text
        return tuple(
            TaxonomyLinkSeed(
                taxonomy_type=taxonomy_type,
                name=value,
                slug=slugify(value),
                description=None,
                link_strength=link_strength,
                evidence_kind=evidence_kind,
                evidence_text=evidence_text,
            )
            for value in matched_values
        )

    def _build_relation_seeds(
        self,
        *,
        source_title: str,
        source_slug: str,
        sections: tuple[NormalizedSection, ...],
        links: tuple[NormalizedLink, ...],
    ) -> tuple[StyleRelationSeed, ...]:
        relation_seeds: list[StyleRelationSeed] = []

        for link in links:
            if link.link_type not in {"wiki_internal", "see_also", "family_hint"}:
                continue

            target_title = _clean_text(link.target_title or link.anchor_text)
            if not target_title:
                continue
            if self._is_non_style_link_title(target_title):
                continue
            if self._is_self_reference(target_title, source_title=source_title, source_slug=source_slug):
                continue
            if self._looks_like_taxonomy_only_title(target_title):
                continue

            sentence, section_title = self._find_context_for_link(
                sections,
                phrase=target_title,
                preferred_section_title=link.section_title,
            )
            relation_type, score = self._classify_relation(
                sentence=sentence,
                section_title=section_title,
                source_title=source_title,
                target_title=target_title,
            )
            if link.link_type == "see_also":
                relation_type = "adjacent_to"
                score = max(score, 0.78)
            elif link.link_type == "family_hint":
                relation_type = "same_family"
                score = max(score, 0.8)

            if not self._is_relation_seed_actionable(
                link=link,
                relation_type=relation_type,
                score=score,
                sentence=sentence,
                section_title=section_title,
            ):
                continue
            relation_seeds.append(
                StyleRelationSeed(
                    target_style_slug=slugify(target_title),
                    relation_type=relation_type,
                    score=score,
                    reason=sentence or f"Internal link to related style {target_title}",
                    evidence_kind="wiki_internal_link",
                    evidence_text=sentence or target_title,
                )
            )

        deduped: dict[tuple[str, str], StyleRelationSeed] = {}
        for seed in relation_seeds:
            key = (seed.target_style_slug, seed.relation_type)
            existing = deduped.get(key)
            if existing is None or seed.score > existing.score:
                deduped[key] = seed
        return self._cap_relation_seeds(tuple(deduped.values()))

    def _find_context_for_link(
        self,
        sections: tuple[NormalizedSection, ...],
        *,
        phrase: str,
        preferred_section_title: str | None,
    ) -> tuple[str | None, str | None]:
        preferred_title = _clean_text(preferred_section_title)
        lowered_preferred_title = preferred_title.casefold()
        if preferred_title:
            for section in sections:
                section_title = _clean_text(section.section_title)
                if section_title.casefold() != lowered_preferred_title:
                    continue
                for sentence in _split_sentences(section.section_text):
                    if phrase.casefold() in sentence.casefold():
                        return sentence, section_title or None
                fallback_sentences = _split_sentences(section.section_text)
                if fallback_sentences:
                    return fallback_sentences[0], section_title or None
                return None, section_title or None
        return self._find_context_for_phrase(sections, phrase=phrase)

    def _find_context_for_phrase(
        self,
        sections: tuple[NormalizedSection, ...],
        *,
        phrase: str,
    ) -> tuple[str | None, str | None]:
        lowered_phrase = phrase.casefold()
        for section in sections:
            for sentence in _split_sentences(section.section_text):
                if lowered_phrase in sentence.casefold():
                    return sentence, _clean_text(section.section_title) or None
        return None, None

    def _classify_relation(
        self,
        *,
        sentence: str | None,
        section_title: str | None,
        source_title: str,
        target_title: str,
    ) -> tuple[str, float]:
        lowered_sentence = self._normalize_relation_context(
            sentence,
            source_title=source_title,
            target_title=target_title,
        ).casefold()
        lowered_section_title = _clean_text(section_title).casefold()

        for phrases, relation_type, score in RELATION_PHRASE_RULES:
            if _contains_any_keyword(lowered_sentence, phrases):
                return relation_type, score

        if _contains_any_keyword(lowered_sentence, PALETTE_RELATION_TERMS):
            return "shares_palette_with", 0.83

        if _contains_any_keyword(lowered_sentence, SILHOUETTE_RELATION_TERMS):
            return "shares_silhouette_with", 0.82

        if any(term in lowered_section_title for term in FAMILY_SECTION_TERMS):
            return "same_family", 0.78
        if any(term in lowered_section_title for term in RELATED_SECTION_TERMS):
            return "adjacent_to", 0.7
        return "adjacent_to", 0.58

    def _normalize_relation_context(
        self,
        sentence: str | None,
        *,
        source_title: str,
        target_title: str,
    ) -> str:
        normalized = _clean_text(sentence)
        for title in (source_title, target_title):
            cleaned_title = _clean_text(title)
            if not cleaned_title:
                continue
            normalized = re.sub(re.escape(cleaned_title), " ", normalized, flags=re.IGNORECASE)
        return _clean_text(normalized)

    def _is_relation_seed_actionable(
        self,
        *,
        link: NormalizedLink,
        relation_type: str,
        score: float,
        sentence: str | None,
        section_title: str | None,
    ) -> bool:
        lowered_section_title = _clean_text(section_title or link.section_title).casefold()
        has_context_sentence = bool(_clean_text(sentence))

        if self._looks_like_navigation_relation_context(sentence):
            return False

        if relation_type in {"inspired_by", "subcategory_of", "historically_related", "contrast_pair", "fusion_candidate"}:
            return has_context_sentence
        if relation_type == "same_family":
            return link.link_type == "family_hint" or any(term in lowered_section_title for term in FAMILY_SECTION_TERMS)
        if relation_type in {"shares_palette_with", "shares_silhouette_with"}:
            return has_context_sentence and score >= 0.8
        if relation_type == "adjacent_to":
            if link.link_type == "see_also":
                return has_context_sentence
            return has_context_sentence and any(term in lowered_section_title for term in RELATED_SECTION_TERMS)
        return score >= 0.72 and has_context_sentence

    def _looks_like_navigation_relation_context(self, text: str | None) -> bool:
        lowered = _clean_text(text).casefold()
        if not lowered:
            return False
        if any(marker in lowered for marker in RELATION_NAVIGATION_MARKERS):
            return True
        if lowered.count("•") >= 2 or lowered.count(",") >= 4:
            return True
        return len(lowered.split()) >= 14 and not any(marker in lowered for marker in ".!?;:")

    def _cap_relation_seeds(self, seeds: tuple[StyleRelationSeed, ...]) -> tuple[StyleRelationSeed, ...]:
        ordered = sorted(seeds, key=lambda item: (item.score, item.relation_type != "adjacent_to"), reverse=True)
        counts_by_type: dict[str, int] = {}
        counts_by_reason_and_type: dict[tuple[str, str], int] = {}
        capped: list[StyleRelationSeed] = []
        for seed in ordered:
            relation_limit = MAX_RELATION_SEEDS_BY_TYPE.get(seed.relation_type)
            if relation_limit is not None and counts_by_type.get(seed.relation_type, 0) >= relation_limit:
                continue
            reason_limit = MAX_RELATION_SEEDS_PER_REASON_BY_TYPE.get(seed.relation_type)
            normalized_reason = _clean_text(seed.reason or seed.evidence_text).casefold()
            if reason_limit is not None and normalized_reason:
                reason_key = (seed.relation_type, normalized_reason)
                if counts_by_reason_and_type.get(reason_key, 0) >= reason_limit:
                    continue
            capped.append(seed)
            counts_by_type[seed.relation_type] = counts_by_type.get(seed.relation_type, 0) + 1
            if reason_limit is not None and normalized_reason:
                counts_by_reason_and_type[reason_key] = counts_by_reason_and_type.get(reason_key, 0) + 1
            if len(capped) >= MAX_RELATION_SEEDS_PER_STYLE:
                break
        return tuple(capped)

    def _match_vocabulary_values(
        self,
        text: str,
        *,
        vocabulary,
    ) -> tuple[str, ...]:
        lowered = _clean_text(text).casefold()
        matched: list[str] = []
        for canonical_value, keywords in vocabulary.values.items():
            if any(keyword.casefold() in lowered for keyword in keywords):
                matched.append(canonical_value)
        return tuple(matched)

    def _is_non_style_link_title(self, title: str) -> bool:
        lowered = title.casefold()
        if any(lowered.startswith(prefix) for prefix in NON_STYLE_LINK_PREFIXES):
            return True
        if ":" in lowered:
            return True
        if re.search(r"\(\d{4}\)", title):
            return True
        return lowered in NON_STYLE_LINK_TITLES

    def _is_self_reference(
        self,
        title: str,
        *,
        source_title: str,
        source_slug: str,
    ) -> bool:
        return slugify(title) in {slugify(source_title), slugify(source_slug.replace("_", " "))}

    def _looks_like_taxonomy_only_title(self, title: str) -> bool:
        return any(
            self._match_vocabulary_values(title, vocabulary=VOCABULARY_BY_TYPE[trait_type])
            for trait_type in ("color", "era", "region")
        )

    def _dedupe_taxonomy_seeds(
        self,
        seeds: tuple[TaxonomyLinkSeed, ...],
    ) -> tuple[TaxonomyLinkSeed, ...]:
        deduped: dict[tuple[str, str], TaxonomyLinkSeed] = {}
        for seed in seeds:
            key = (seed.taxonomy_type, seed.slug)
            existing = deduped.get(key)
            if existing is None or seed.link_strength > existing.link_strength:
                deduped[key] = seed
        return tuple(deduped.values())

    def _build_image_prompt_notes(
        self,
        grouped_values: dict[str, tuple[str, ...]],
    ) -> tuple[str, ...]:
        notes: list[str] = []
        if grouped_values.get("color"):
            notes.append("palette: " + ", ".join(grouped_values["color"][:4]))
        if grouped_values.get("material"):
            notes.append("materials: " + ", ".join(grouped_values["material"][:4]))
        if grouped_values.get("silhouette"):
            notes.append("silhouette: " + ", ".join(grouped_values["silhouette"][:3]))
        if grouped_values.get("garment"):
            notes.append("core garments: " + ", ".join(grouped_values["garment"][:4]))
        if grouped_values.get("motif"):
            notes.append("motifs/textures: " + ", ".join(grouped_values["motif"][:3]))
        if grouped_values.get("art_reference"):
            notes.append("art references: " + ", ".join(grouped_values["art_reference"][:3]))
        if grouped_values.get("composition_hint"):
            notes.append("composition: " + ", ".join(grouped_values["composition_hint"][:3]))
        if grouped_values.get("seasonality"):
            notes.append("seasonality: " + ", ".join(grouped_values["seasonality"][:2]))
        return tuple(notes)


def _truncate(value: str | None, limit: int) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 3:
        return cleaned[:limit]
    return cleaned[: limit - 3].rstrip() + "..."
