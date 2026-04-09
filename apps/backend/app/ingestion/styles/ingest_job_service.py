from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_ingest_attempt import StyleIngestAttempt
from app.models.style_ingest_job import StyleIngestJob
from app.models.style_source_page import StyleSourcePage
from app.models.style_source_page_version import StyleSourcePageVersion


QUEUED_STATUS = "queued"
RUNNING_STATUS = "running"
SUCCEEDED_STATUS = "succeeded"
SOFT_FAILED_STATUS = "soft_failed"
HARD_FAILED_STATUS = "hard_failed"
COOLDOWN_DEFERRED_STATUS = "cooldown_deferred"

ACTIVE_JOB_STATUSES = {QUEUED_STATUS, RUNNING_STATUS, COOLDOWN_DEFERRED_STATUS}
TERMINAL_JOB_STATUSES = {SUCCEEDED_STATUS, SOFT_FAILED_STATUS, HARD_FAILED_STATUS}


class StyleIngestJobService:
    async def reclaim_stale_running_jobs(
        self,
        session: AsyncSession,
        *,
        stale_after_seconds: float,
        source_name: str | None = None,
        job_type: str | None = None,
        now: datetime | None = None,
        limit: int = 25,
    ) -> int:
        current_time = now or datetime.now(UTC)
        stale_cutoff = current_time - timedelta(seconds=max(float(stale_after_seconds), 1.0))
        query = (
            select(StyleIngestJob)
            .where(
                StyleIngestJob.status == RUNNING_STATUS,
                StyleIngestJob.locked_at.is_not(None),
                StyleIngestJob.locked_at <= stale_cutoff,
            )
            .order_by(StyleIngestJob.locked_at.asc(), StyleIngestJob.id.asc())
            .with_for_update(skip_locked=True)
        )
        if source_name:
            query = query.where(StyleIngestJob.source_name == source_name)
        if job_type:
            query = query.where(StyleIngestJob.job_type == job_type)

        jobs = (await session.execute(query.limit(max(int(limit), 1)))).scalars().all()
        if not jobs:
            return 0

        reclaimed_count = 0
        for job in jobs:
            attempt = (
                await session.execute(
                    select(StyleIngestAttempt)
                    .where(StyleIngestAttempt.job_id == job.id)
                    .order_by(StyleIngestAttempt.attempt_number.desc(), StyleIngestAttempt.id.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if attempt is not None and attempt.status == RUNNING_STATUS:
                attempt.status = SOFT_FAILED_STATUS
                attempt.finished_at = current_time
                attempt.error_class = "stale_running_job"
                attempt.error_message = (
                    f"Job was reclaimed after exceeding stale running timeout "
                    f"({int(max(float(stale_after_seconds), 1.0))}s)"
                )
                attempt.cooldown_until = current_time
                session.add(attempt)

            job.status = QUEUED_STATUS
            job.locked_at = None
            job.finished_at = None
            job.available_at = current_time
            job.last_error_class = "stale_running_job"
            job.last_error_message = "Job was returned to queue after worker restart or timeout"
            session.add(job)
            reclaimed_count += 1

        await session.flush()
        return reclaimed_count

    async def upsert_source_page(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        page_url: str,
        source_title: str,
        page_kind: str,
        remote_page_id: int | None = None,
        discovered_at: datetime | None = None,
    ) -> StyleSourcePage:
        result = await session.execute(
            select(StyleSourcePage).where(
                StyleSourcePage.source_name == source_name,
                StyleSourcePage.page_url == page_url,
            )
        )
        page = result.scalar_one_or_none()
        now = discovered_at or datetime.now(UTC)
        if page is None:
            page = StyleSourcePage(
                source_name=source_name,
                page_url=page_url,
                source_title=source_title,
                page_kind=page_kind,
                remote_page_id=remote_page_id,
                last_discovered_at=now,
            )
        else:
            page.source_title = source_title
            page.page_kind = page_kind
            page.remote_page_id = remote_page_id
            page.last_discovered_at = now
        session.add(page)
        await session.flush()
        return page

    async def register_page_version(
        self,
        session: AsyncSession,
        *,
        source_page: StyleSourcePage,
        fetch_mode: str,
        remote_revision_id: int | None,
        content_fingerprint: str | None,
        raw_html: str,
        raw_wikitext: str | None,
        raw_text: str | None,
        raw_sections_json: list[dict] | None = None,
        raw_links_json: list[dict] | None = None,
        fetched_at: datetime | None = None,
    ) -> StyleSourcePageVersion:
        query = select(StyleSourcePageVersion).where(StyleSourcePageVersion.source_page_id == source_page.id)
        if remote_revision_id is not None:
            query = query.where(StyleSourcePageVersion.remote_revision_id == remote_revision_id)
        elif content_fingerprint is not None:
            query = query.where(StyleSourcePageVersion.content_fingerprint == content_fingerprint)
        else:
            query = query.where(StyleSourcePageVersion.id == -1)

        version = (await session.execute(query.limit(1))).scalar_one_or_none()
        if version is None:
            version = StyleSourcePageVersion(
                source_page_id=source_page.id,
                fetch_mode=fetch_mode,
                remote_revision_id=remote_revision_id,
                content_fingerprint=content_fingerprint,
                fetched_at=fetched_at or datetime.now(UTC),
                raw_html=raw_html,
                raw_wikitext=raw_wikitext,
                raw_text=raw_text,
                raw_sections_json=list(raw_sections_json or []),
                raw_links_json=list(raw_links_json or []),
            )
        else:
            version.fetch_mode = fetch_mode
            version.content_fingerprint = content_fingerprint
            version.fetched_at = fetched_at or datetime.now(UTC)
            version.raw_html = raw_html
            version.raw_wikitext = raw_wikitext
            version.raw_text = raw_text
            version.raw_sections_json = list(raw_sections_json or [])
            version.raw_links_json = list(raw_links_json or [])

        source_page.last_fetched_at = version.fetched_at
        source_page.latest_revision_id = remote_revision_id
        source_page.latest_content_fingerprint = content_fingerprint

        session.add(source_page)
        session.add(version)
        await session.flush()
        return version

    async def enqueue_job(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        job_type: str,
        dedupe_key: str,
        payload_json: dict | None = None,
        source_page_id: int | None = None,
        source_page_version_id: int | None = None,
        priority: int = 100,
        available_at: datetime | None = None,
    ) -> StyleIngestJob:
        result = await session.execute(select(StyleIngestJob).where(StyleIngestJob.dedupe_key == dedupe_key).limit(1))
        job = result.scalar_one_or_none()
        if job is not None:
            return job

        job = StyleIngestJob(
            source_name=source_name,
            job_type=job_type,
            dedupe_key=dedupe_key,
            status=QUEUED_STATUS,
            payload_json=payload_json,
            priority=priority,
            available_at=available_at or datetime.now(UTC),
            source_page_id=source_page_id,
            source_page_version_id=source_page_version_id,
        )
        session.add(job)
        await session.flush()
        return job

    async def claim_next_job(
        self,
        session: AsyncSession,
        *,
        source_name: str | None = None,
        job_type: str | None = None,
        now: datetime | None = None,
    ) -> tuple[StyleIngestJob, StyleIngestAttempt] | None:
        current_time = now or datetime.now(UTC)
        query = (
            select(StyleIngestJob)
            .where(
                StyleIngestJob.status.in_((QUEUED_STATUS, COOLDOWN_DEFERRED_STATUS)),
                StyleIngestJob.available_at <= current_time,
            )
            .order_by(
                StyleIngestJob.priority.asc(),
                StyleIngestJob.available_at.asc(),
                StyleIngestJob.id.asc(),
            )
            .with_for_update(skip_locked=True)
        )
        if source_name:
            query = query.where(StyleIngestJob.source_name == source_name)
        if job_type:
            query = query.where(StyleIngestJob.job_type == job_type)

        job = (await session.execute(query.limit(1))).scalar_one_or_none()
        if job is None:
            return None

        job.status = RUNNING_STATUS
        job.locked_at = current_time
        job.started_at = job.started_at or current_time
        job.attempt_count += 1

        attempt = StyleIngestAttempt(
            job_id=job.id,
            attempt_number=job.attempt_count,
            status=RUNNING_STATUS,
            started_at=current_time,
        )
        session.add(job)
        session.add(attempt)
        await session.flush()
        return job, attempt

    async def mark_job_succeeded(
        self,
        session: AsyncSession,
        *,
        job: StyleIngestJob,
        attempt: StyleIngestAttempt,
        finished_at: datetime | None = None,
    ) -> None:
        now = finished_at or datetime.now(UTC)
        job.status = SUCCEEDED_STATUS
        job.finished_at = now
        job.locked_at = None
        job.last_error_class = None
        job.last_error_message = None

        attempt.status = SUCCEEDED_STATUS
        attempt.finished_at = now
        session.add(job)
        session.add(attempt)
        await session.flush()

    async def mark_job_terminal(
        self,
        session: AsyncSession,
        *,
        job: StyleIngestJob,
        attempt: StyleIngestAttempt,
        status: str,
        http_status: int | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
        cooldown_until: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        if status not in {SOFT_FAILED_STATUS, HARD_FAILED_STATUS, COOLDOWN_DEFERRED_STATUS}:
            raise ValueError(f"Unsupported terminal status {status!r}")

        now = finished_at or datetime.now(UTC)
        job.status = status
        job.finished_at = now if status != COOLDOWN_DEFERRED_STATUS else None
        job.locked_at = None
        job.available_at = cooldown_until or job.available_at
        job.last_error_class = error_class
        job.last_error_message = error_message

        attempt.status = status
        attempt.finished_at = now
        attempt.http_status = http_status
        attempt.error_class = error_class
        attempt.error_message = error_message
        attempt.cooldown_until = cooldown_until

        session.add(job)
        session.add(attempt)
        await session.flush()

    async def mark_job_requeued(
        self,
        session: AsyncSession,
        *,
        job: StyleIngestJob,
        attempt: StyleIngestAttempt,
        available_at: datetime,
        http_status: int | None = None,
        error_class: str | None = None,
        error_message: str | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        now = finished_at or datetime.now(UTC)
        job.status = QUEUED_STATUS
        job.finished_at = None
        job.locked_at = None
        job.available_at = available_at
        job.last_error_class = error_class
        job.last_error_message = error_message

        attempt.status = SOFT_FAILED_STATUS
        attempt.finished_at = now
        attempt.http_status = http_status
        attempt.error_class = error_class
        attempt.error_message = error_message
        attempt.cooldown_until = available_at

        session.add(job)
        session.add(attempt)
        await session.flush()
