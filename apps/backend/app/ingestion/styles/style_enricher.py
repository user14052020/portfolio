from slugify import slugify

from app.ingestion.styles.contracts import EnrichedStyleDocument, NormalizedStyleDocument, StyleEnricher
from app.ingestion.styles.style_feature_extractor import StyleFeatureExtractor


def _truncate(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if len(cleaned) <= limit:
        return cleaned
    if limit <= 3:
        return cleaned[:limit]
    return cleaned[: limit - 3].rstrip() + "..."


class DefaultStyleEnricher(StyleEnricher):
    def __init__(self) -> None:
        self.feature_extractor = StyleFeatureExtractor()

    def enrich(self, normalized: NormalizedStyleDocument) -> EnrichedStyleDocument:
        canonical_name = normalized.source_title.strip()
        display_name = canonical_name
        slug = slugify(canonical_name) or slugify(normalized.source_url.rsplit("/", 1)[-1]) or "style"

        first_section_text = None
        for section in normalized.sections:
            if section.section_text.strip():
                first_section_text = section.section_text.strip()
                break
        if first_section_text is None:
            first_section_text = normalized.raw_text.strip()

        short_definition = _truncate(first_section_text, 280)
        long_summary = _truncate(normalized.raw_text, 2400)
        semantic_bundle = self.feature_extractor.extract(normalized)
        confidence_score = self._compute_confidence_score(
            normalized=normalized,
            profile_payload=semantic_bundle.profile_payload,
            short_definition=short_definition,
            long_summary=long_summary,
            trait_count=len(semantic_bundle.trait_seeds),
            taxonomy_count=len(semantic_bundle.taxonomy_link_seeds),
            relation_count=len(semantic_bundle.relation_seeds),
        )

        alias_candidates = tuple(
            dict.fromkeys(
                candidate
                for candidate in (
                    canonical_name,
                    display_name,
                    normalized.source_title.strip(),
                )
                if candidate
            )
        )

        return EnrichedStyleDocument(
            normalized=normalized,
            canonical_name=canonical_name,
            slug=slug,
            display_name=display_name,
            short_definition=short_definition,
            long_summary=long_summary,
            alias_candidates=alias_candidates,
            profile_payload=semantic_bundle.profile_payload,
            confidence_score=confidence_score,
            trait_seeds=semantic_bundle.trait_seeds,
            taxonomy_link_seeds=semantic_bundle.taxonomy_link_seeds,
            relation_seeds=semantic_bundle.relation_seeds,
        )

    def _compute_confidence_score(
        self,
        *,
        normalized: NormalizedStyleDocument,
        profile_payload: dict[str, object],
        short_definition: str | None,
        long_summary: str | None,
        trait_count: int,
        taxonomy_count: int,
        relation_count: int,
    ) -> float:
        score = 0.0
        raw_text_length = len(normalized.raw_text.strip())
        section_count = len(normalized.sections)

        if raw_text_length >= 1600:
            score += 0.14
        elif raw_text_length >= 800:
            score += 0.1
        elif raw_text_length >= 300:
            score += 0.05

        if section_count >= 6:
            score += 0.14
        elif section_count >= 3:
            score += 0.1
        elif section_count >= 1:
            score += 0.05

        if short_definition:
            score += 0.08
        if long_summary:
            score += 0.06

        for field_name in (
            "essence",
            "fashion_summary",
            "visual_summary",
            "historical_context",
            "cultural_context",
        ):
            if profile_payload.get(field_name):
                score += 0.06

        score += min(0.22, trait_count * 0.02)
        score += min(0.1, taxonomy_count * 0.025)
        score += min(0.08, relation_count * 0.02)

        for field_name in (
            "color_palette_json",
            "materials_json",
            "silhouettes_json",
            "garments_json",
            "occasion_fit_json",
            "seasonality_json",
            "hair_makeup_json",
        ):
            values = profile_payload.get(field_name)
            if isinstance(values, list) and values:
                score += 0.012

        return round(min(score, 0.98), 4)
