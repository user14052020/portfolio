from app.ingestion.styles.contracts import EnrichedStyleDocument, StyleValidator, ValidatedStyleDocument


class DefaultStyleValidator(StyleValidator):
    def validate(self, enriched: EnrichedStyleDocument) -> ValidatedStyleDocument:
        warnings: list[str] = []
        errors: list[str] = []

        if not enriched.canonical_name.strip():
            errors.append("canonical_name is empty")
        if not enriched.slug.strip():
            errors.append("slug is empty")
        if not enriched.normalized.source_url.strip():
            errors.append("source_url is empty")
        if not enriched.normalized.raw_text.strip():
            errors.append("raw_text is empty")

        if len(enriched.normalized.raw_text.strip()) < 300:
            warnings.append("raw_text is shorter than 300 characters")
        if not enriched.normalized.sections:
            warnings.append("no normalized sections extracted")
        if not enriched.alias_candidates:
            warnings.append("no alias candidates derived")
        if enriched.confidence_score < 0.55:
            warnings.append(f"confidence_score is low: {enriched.confidence_score:.4f}")
        if len(enriched.trait_seeds) < 3:
            warnings.append("fewer than 3 semantic traits extracted")
        if not enriched.taxonomy_link_seeds:
            warnings.append("no taxonomy links extracted")
        if not enriched.relation_seeds:
            warnings.append("no style relations extracted")

        if (
            enriched.confidence_score < 0.2
            or (
                not enriched.profile_payload.get("essence")
                and not enriched.profile_payload.get("fashion_summary")
                and len(enriched.trait_seeds) == 0
            )
        ):
            errors.append("semantic coverage is insufficient for production ingestion")

        return ValidatedStyleDocument(
            enriched=enriched,
            is_valid=not errors,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )
