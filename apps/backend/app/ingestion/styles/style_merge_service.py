from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import StyleDirectionMergeItem, StyleDirectionMergeReport
from app.models.style import Style
from app.models.style_alias import StyleAlias
from app.models.style_direction import StyleDirection
from app.models.style_direction_match import StyleDirectionMatch
from app.models.style_direction_style_link import StyleDirectionStyleLink
from app.models.style_source import StyleSource


ELIGIBLE_MATCH_STATUSES = ("auto_matched", "manual_confirmed")
MANUAL_LINK_STATUSES = {"manual_linked", "manual_locked"}


class StyleDirectionMergeService:
    async def merge_matches(
        self,
        session: AsyncSession,
        *,
        source_name: str | None = None,
        limit: int = 100,
        persist: bool,
    ) -> StyleDirectionMergeReport:
        matches = await self._load_merge_candidates(session, source_name=source_name, limit=limit)
        items: list[StyleDirectionMergeItem] = []
        merged_count = 0
        skipped_count = 0

        for match, style_direction, canonical_style in matches:
            item = await self._merge_single(
                session,
                match=match,
                style_direction=style_direction,
                canonical_style=canonical_style,
                persist=persist,
            )
            items.append(item)
            if item.merge_status in {"linked", "updated_link"}:
                merged_count += 1
            else:
                skipped_count += 1

        return StyleDirectionMergeReport(
            selected_count=len(items),
            merged_count=merged_count,
            skipped_count=skipped_count,
            items=tuple(items),
        )

    async def _load_merge_candidates(
        self,
        session: AsyncSession,
        *,
        source_name: str | None,
        limit: int,
    ) -> list[tuple[StyleDirectionMatch, StyleDirection | None, Style | None]]:
        statement = (
            select(StyleDirectionMatch, StyleDirection, Style)
            .join(StyleDirection, StyleDirection.id == StyleDirectionMatch.style_direction_id, isouter=True)
            .join(StyleSource, StyleSource.source_url == StyleDirectionMatch.source_url, isouter=True)
            .join(Style, Style.source_primary_id == StyleSource.id, isouter=True)
            .where(StyleDirectionMatch.match_status.in_(ELIGIBLE_MATCH_STATUSES))
            .order_by(StyleDirectionMatch.reviewed_at.asc().nullsfirst(), StyleDirectionMatch.updated_at.asc())
            .limit(limit)
        )
        if source_name:
            statement = statement.where(StyleDirectionMatch.source_name == source_name)
        result = await session.execute(statement)
        return [(match, direction, style) for match, direction, style in result.all()]

    async def _merge_single(
        self,
        session: AsyncSession,
        *,
        match: StyleDirectionMatch,
        style_direction: StyleDirection | None,
        canonical_style: Style | None,
        persist: bool,
    ) -> StyleDirectionMergeItem:
        if match.style_direction_id is None or style_direction is None:
            return self._build_item(
                match=match,
                canonical_style=canonical_style,
                merge_status="missing_style_direction",
                link_status=None,
            )

        if canonical_style is None:
            return self._build_item(
                match=match,
                canonical_style=None,
                merge_status="missing_canonical_style",
                link_status=None,
            )

        existing_link = await self._get_existing_link(session, style_direction_id=style_direction.id)
        desired_link_status = "manual_linked" if match.match_status == "manual_confirmed" else "auto_linked"

        if existing_link is not None and existing_link.link_status in MANUAL_LINK_STATUSES:
            return self._build_item(
                match=match,
                canonical_style=canonical_style,
                merge_status="manual_link_preserved",
                link_status=existing_link.link_status,
            )

        merge_status = "linked"
        if existing_link is not None:
            if existing_link.style_id == canonical_style.id and existing_link.link_status == desired_link_status:
                merge_status = "already_linked"
            else:
                merge_status = "updated_link"

        if persist and merge_status != "already_linked":
            if existing_link is None:
                existing_link = StyleDirectionStyleLink(
                    style_direction_id=style_direction.id,
                    style_id=canonical_style.id,
                )
            existing_link.style_id = canonical_style.id
            existing_link.linked_via_match_id = match.id
            existing_link.link_status = desired_link_status
            existing_link.link_method = match.match_method
            existing_link.confidence_score = match.match_score
            existing_link.link_note = match.review_note
            session.add(existing_link)
            await self._ensure_legacy_aliases(
                session,
                style=canonical_style,
                style_direction=style_direction,
            )
            await session.flush()

        return self._build_item(
            match=match,
            canonical_style=canonical_style,
            merge_status=merge_status,
            link_status=desired_link_status if merge_status != "manual_link_preserved" else existing_link.link_status,
        )

    async def _get_existing_link(
        self,
        session: AsyncSession,
        *,
        style_direction_id: int,
    ) -> StyleDirectionStyleLink | None:
        result = await session.execute(
            select(StyleDirectionStyleLink)
            .where(StyleDirectionStyleLink.style_direction_id == style_direction_id)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _ensure_legacy_aliases(
        self,
        session: AsyncSession,
        *,
        style: Style,
        style_direction: StyleDirection,
    ) -> None:
        for alias_value in self._legacy_alias_candidates(style_direction):
            exists = await session.execute(
                select(StyleAlias)
                .where(
                    StyleAlias.style_id == style.id,
                    StyleAlias.alias == alias_value,
                    StyleAlias.language.is_(None),
                )
                .limit(1)
            )
            if exists.scalar_one_or_none() is not None:
                continue
            session.add(
                StyleAlias(
                    style_id=style.id,
                    alias=alias_value,
                    alias_type="db_import_name",
                    language=None,
                    is_primary_match_hint=False,
                )
            )

    def _legacy_alias_candidates(self, style_direction: StyleDirection) -> tuple[str, ...]:
        deduped: dict[str, str] = {}
        for value in (style_direction.source_title, style_direction.title_en):
            normalized = (value or "").strip()
            if not normalized:
                continue
            deduped[normalized.casefold()] = normalized
        return tuple(deduped.values())

    def _build_item(
        self,
        *,
        match: StyleDirectionMatch,
        canonical_style: Style | None,
        merge_status: str,
        link_status: str | None,
    ) -> StyleDirectionMergeItem:
        return StyleDirectionMergeItem(
            match_id=match.id,
            source_name=match.source_name,
            source_url=match.source_url,
            source_title=match.source_title,
            discovered_slug=match.discovered_slug,
            match_status=match.match_status,
            style_direction_id=match.style_direction_id,
            canonical_style_id=None if canonical_style is None else canonical_style.id,
            canonical_style_slug=None if canonical_style is None else canonical_style.slug,
            merge_status=merge_status,
            link_status=link_status,
            confidence_score=match.match_score,
        )
