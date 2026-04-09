from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.styles.contracts import (
    StyleDirectionMatchOption,
    StyleDirectionReviewQueueItem,
    StyleDirectionReviewResolutionResult,
)
from app.models.style_direction_match import StyleDirectionMatch
from app.models.style_direction_match_review import StyleDirectionMatchReview


PENDING_REVIEW_STATUS = "pending"
RESOLVED_REVIEW_STATUS = "resolved"
SUPERSEDED_REVIEW_STATUS = "superseded"

CONFIRM_RESOLUTION = "confirm_candidate"
REJECT_RESOLUTION = "reject_candidate"


class StyleDirectionReviewService:
    async def sync_for_match(
        self,
        session: AsyncSession,
        *,
        match: StyleDirectionMatch,
    ) -> StyleDirectionMatchReview | None:
        review = await self._get_review_by_match_id(session, match_id=match.id)
        now = datetime.now(UTC)

        if match.match_status == "ambiguous":
            if review is None:
                review = StyleDirectionMatchReview(
                    match_id=match.id,
                    review_status=PENDING_REVIEW_STATUS,
                    queued_at=now,
                )
            elif review.review_status == SUPERSEDED_REVIEW_STATUS:
                review.review_status = PENDING_REVIEW_STATUS
                review.resolution_type = None
                review.selected_style_direction_id = None
                review.resolution_note = None
                review.queued_at = now
                review.resolved_at = None
            session.add(review)
            await session.flush()
            return review

        if review is not None and review.review_status == PENDING_REVIEW_STATUS:
            review.review_status = SUPERSEDED_REVIEW_STATUS
            review.resolved_at = now
            session.add(review)
            await session.flush()

        return review

    async def list_pending_reviews(
        self,
        session: AsyncSession,
        *,
        limit: int = 50,
        source_name: str | None = None,
    ) -> tuple[StyleDirectionReviewQueueItem, ...]:
        statement = (
            select(StyleDirectionMatchReview, StyleDirectionMatch)
            .join(StyleDirectionMatch, StyleDirectionMatch.id == StyleDirectionMatchReview.match_id)
            .where(StyleDirectionMatchReview.review_status == PENDING_REVIEW_STATUS)
            .order_by(StyleDirectionMatchReview.queued_at.asc(), StyleDirectionMatchReview.id.asc())
            .limit(limit)
        )
        if source_name:
            statement = statement.where(StyleDirectionMatch.source_name == source_name)

        result = await session.execute(statement)
        return tuple(self._serialize_queue_item(review=review, match=match) for review, match in result.all())

    async def resolve_review(
        self,
        session: AsyncSession,
        *,
        match_id: int,
        resolution: str,
        selected_style_direction_id: int | None = None,
        review_note: str | None = None,
    ) -> StyleDirectionReviewResolutionResult:
        review, match = await self._get_pending_review_pair(session, match_id=match_id)
        if review is None or match is None:
            raise ValueError("Pending manual review item was not found for the requested match_id")

        now = datetime.now(UTC)

        if resolution == CONFIRM_RESOLUTION:
            if selected_style_direction_id is None:
                raise ValueError("selected_style_direction_id is required for confirm_candidate resolution")
            selected_option = self._find_candidate_option(match, selected_style_direction_id)
            if selected_option is None:
                raise ValueError("selected_style_direction_id is not present in candidate_snapshot_json")
            match.style_direction_id = selected_option.style_direction_id
            match.match_status = "manual_confirmed"
            match.match_method = "manual_review"
            match.match_score = selected_option.match_score
        elif resolution == REJECT_RESOLUTION:
            selected_style_direction_id = None
            match.style_direction_id = None
            match.match_status = "manual_rejected"
            match.match_method = "manual_review"
        else:
            raise ValueError(f"Unsupported manual review resolution={resolution!r}")

        match.review_note = review_note
        match.reviewed_at = now

        review.review_status = RESOLVED_REVIEW_STATUS
        review.resolution_type = resolution
        review.selected_style_direction_id = selected_style_direction_id
        review.resolution_note = review_note
        review.resolved_at = now

        session.add(match)
        session.add(review)
        await session.flush()

        return StyleDirectionReviewResolutionResult(
            review_id=review.id,
            match_id=match.id,
            source_name=match.source_name,
            source_url=match.source_url,
            source_title=match.source_title,
            discovered_slug=match.discovered_slug,
            review_status=review.review_status,
            match_status=match.match_status,
            selected_style_direction_id=selected_style_direction_id,
            resolution_type=resolution,
        )

    async def _get_review_by_match_id(
        self,
        session: AsyncSession,
        *,
        match_id: int,
    ) -> StyleDirectionMatchReview | None:
        result = await session.execute(
            select(StyleDirectionMatchReview).where(StyleDirectionMatchReview.match_id == match_id).limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_pending_review_pair(
        self,
        session: AsyncSession,
        *,
        match_id: int,
    ) -> tuple[StyleDirectionMatchReview | None, StyleDirectionMatch | None]:
        result = await session.execute(
            select(StyleDirectionMatchReview, StyleDirectionMatch)
            .join(StyleDirectionMatch, StyleDirectionMatch.id == StyleDirectionMatchReview.match_id)
            .where(
                StyleDirectionMatchReview.match_id == match_id,
                StyleDirectionMatchReview.review_status == PENDING_REVIEW_STATUS,
            )
            .limit(1)
        )
        pair = result.first()
        if pair is None:
            return None, None
        return pair[0], pair[1]

    def _serialize_queue_item(
        self,
        *,
        review: StyleDirectionMatchReview,
        match: StyleDirectionMatch,
    ) -> StyleDirectionReviewQueueItem:
        return StyleDirectionReviewQueueItem(
            review_id=review.id,
            match_id=match.id,
            source_name=match.source_name,
            source_url=match.source_url,
            source_title=match.source_title,
            discovered_slug=match.discovered_slug,
            review_status=review.review_status,
            match_status=match.match_status,
            queued_at=review.queued_at,
            candidate_count=match.candidate_count,
            candidate_options=self._candidate_options(match),
        )

    def _candidate_options(self, match: StyleDirectionMatch) -> tuple[StyleDirectionMatchOption, ...]:
        options: list[StyleDirectionMatchOption] = []
        for item in match.candidate_snapshot_json or []:
            try:
                options.append(
                    StyleDirectionMatchOption(
                        style_direction_id=int(item["style_direction_id"]),
                        style_direction_slug=str(item["style_direction_slug"]),
                        style_direction_title=str(item["style_direction_title"]),
                        match_method=str(item["match_method"]),
                        match_score=float(item["match_score"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(options)

    def _find_candidate_option(
        self,
        match: StyleDirectionMatch,
        selected_style_direction_id: int,
    ) -> StyleDirectionMatchOption | None:
        for option in self._candidate_options(match):
            if option.style_direction_id == selected_style_direction_id:
                return option
        return None
