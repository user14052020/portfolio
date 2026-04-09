from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import (
    CandidateBatchSelection,
    DiscoveredStyleCandidate,
    MatchBatchReport,
    StyleDirectionMatchDecision,
    StyleDirectionMatchOption,
)
from app.models.style_direction import StyleDirection
from app.models.style_direction_match import StyleDirectionMatch
from app.ingestion.styles.style_review_service import StyleDirectionReviewService
from app.utils.slug import build_slug


MANUAL_STATUSES = {"manual_confirmed", "manual_rejected"}


def _normalize_name(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[_/\\-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def _build_candidate_slug(value: str) -> str:
    return build_slug(_normalize_name(value) or value)


@dataclass(frozen=True)
class _CatalogEntry:
    style_direction_id: int
    slug: str
    source_title: str
    title_en: str

    @property
    def preferred_title(self) -> str:
        return self.title_en or self.source_title or self.slug

    @property
    def alias_keys(self) -> tuple[tuple[str, str, float], ...]:
        keys: list[tuple[str, str, float]] = []
        if self.slug:
            keys.append((self.slug, "slug_exact", 1.0))

        source_title_normalized = _normalize_name(self.source_title)
        if source_title_normalized:
            keys.append((source_title_normalized, "source_title_exact", 0.97))
            keys.append((_build_candidate_slug(self.source_title), "source_title_slug", 0.95))

        title_en_normalized = _normalize_name(self.title_en)
        if title_en_normalized:
            keys.append((title_en_normalized, "title_en_exact", 0.96))
            keys.append((_build_candidate_slug(self.title_en), "title_en_slug", 0.94))

        deduped: dict[tuple[str, str], tuple[str, str, float]] = {}
        for key_value, match_method, match_score in keys:
            if not key_value:
                continue
            deduped[(key_value, match_method)] = (key_value, match_method, match_score)
        return tuple(deduped.values())


class StyleDirectionMatcher:
    def __init__(self) -> None:
        self.review_service = StyleDirectionReviewService()

    async def match_candidate(
        self,
        session: AsyncSession,
        *,
        candidate: DiscoveredStyleCandidate,
    ) -> StyleDirectionMatchDecision:
        catalog_entries = await self._load_catalog_entries(session)
        options_by_direction_id: dict[int, StyleDirectionMatchOption] = {}

        candidate_normalized_title = _normalize_name(candidate.source_title)
        candidate_slug = _build_candidate_slug(candidate.source_title)
        candidate_keys = {candidate_normalized_title, candidate_slug}

        for entry in catalog_entries:
            for key_value, match_method, match_score in entry.alias_keys:
                if key_value not in candidate_keys:
                    continue
                current = options_by_direction_id.get(entry.style_direction_id)
                option = StyleDirectionMatchOption(
                    style_direction_id=entry.style_direction_id,
                    style_direction_slug=entry.slug,
                    style_direction_title=entry.preferred_title,
                    match_method=match_method,
                    match_score=match_score,
                )
                if current is None or option.match_score > current.match_score:
                    options_by_direction_id[entry.style_direction_id] = option

        options = tuple(
            sorted(
                options_by_direction_id.values(),
                key=lambda item: (-item.match_score, item.style_direction_title.casefold(), item.style_direction_id),
            )
        )

        if not options:
            return StyleDirectionMatchDecision(
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                source_title=candidate.source_title,
                discovered_slug=candidate_slug,
                match_status="unmatched",
                candidate_count=0,
                candidate_options=(),
            )

        top_option = options[0]
        ambiguous = False
        if len(options) > 1:
            second_option = options[1]
            if top_option.match_score == second_option.match_score:
                ambiguous = True
            elif top_option.match_score < 0.96 and (top_option.match_score - second_option.match_score) < 0.03:
                ambiguous = True

        if ambiguous:
            return StyleDirectionMatchDecision(
                source_name=candidate.source_name,
                source_url=candidate.source_url,
                source_title=candidate.source_title,
                discovered_slug=candidate_slug,
                match_status="ambiguous",
                matched_style_direction_id=None,
                match_method=None,
                match_score=top_option.match_score,
                candidate_count=len(options),
                candidate_options=options[:5],
            )

        return StyleDirectionMatchDecision(
            source_name=candidate.source_name,
            source_url=candidate.source_url,
            source_title=candidate.source_title,
            discovered_slug=candidate_slug,
            match_status="auto_matched",
            matched_style_direction_id=top_option.style_direction_id,
            match_method=top_option.match_method,
            match_score=top_option.match_score,
            candidate_count=len(options),
            candidate_options=options[:5],
        )

    async def persist_decision(
        self,
        session: AsyncSession,
        *,
        decision: StyleDirectionMatchDecision,
    ) -> StyleDirectionMatch:
        existing = await self._get_existing_match(
            session,
            source_name=decision.source_name,
            source_url=decision.source_url,
        )
        if existing is not None and existing.match_status in MANUAL_STATUSES:
            return existing

        payload = {
            "source_name": decision.source_name,
            "source_url": decision.source_url,
            "source_title": decision.source_title,
            "discovered_slug": decision.discovered_slug,
            "style_direction_id": decision.matched_style_direction_id,
            "match_status": decision.match_status,
            "match_method": decision.match_method,
            "match_score": decision.match_score,
            "candidate_count": decision.candidate_count,
            "candidate_snapshot_json": [
                {
                    "style_direction_id": option.style_direction_id,
                    "style_direction_slug": option.style_direction_slug,
                    "style_direction_title": option.style_direction_title,
                    "match_method": option.match_method,
                    "match_score": option.match_score,
                }
                for option in decision.candidate_options
            ],
        }

        if existing is None:
            existing = StyleDirectionMatch(**payload)
        else:
            for key, value in payload.items():
                setattr(existing, key, value)
        session.add(existing)
        await session.flush()
        await self.review_service.sync_for_match(session, match=existing)
        return existing

    async def match_selection(
        self,
        session: AsyncSession,
        *,
        selection: CandidateBatchSelection,
        persist: bool,
    ) -> MatchBatchReport:
        decisions: list[StyleDirectionMatchDecision] = []
        auto_matched_count = 0
        ambiguous_count = 0
        unmatched_count = 0

        for candidate in selection.candidates:
            decision = await self.match_candidate(session, candidate=candidate)
            if persist:
                await self.persist_decision(session, decision=decision)
            decisions.append(decision)

            if decision.match_status == "auto_matched":
                auto_matched_count += 1
            elif decision.match_status == "ambiguous":
                ambiguous_count += 1
            else:
                unmatched_count += 1

        return MatchBatchReport(
            source_name=selection.source.source_name,
            discovered_count=selection.discovered_count,
            selected_count=selection.selected_count,
            auto_matched_count=auto_matched_count,
            ambiguous_count=ambiguous_count,
            unmatched_count=unmatched_count,
            decisions=tuple(decisions),
        )

    async def _load_catalog_entries(self, session: AsyncSession) -> tuple[_CatalogEntry, ...]:
        result = await session.execute(
            select(StyleDirection).where(StyleDirection.is_active.is_(True)).order_by(StyleDirection.id.asc())
        )
        return tuple(
            _CatalogEntry(
                style_direction_id=item.id,
                slug=item.slug,
                source_title=item.source_title,
                title_en=item.title_en,
            )
            for item in result.scalars().all()
        )

    async def _get_existing_match(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        source_url: str,
    ) -> StyleDirectionMatch | None:
        result = await session.execute(
            select(StyleDirectionMatch)
            .where(
                StyleDirectionMatch.source_name == source_name,
                StyleDirectionMatch.source_url == source_url,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
