from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.style_source_fetch_log import StyleSourceFetchLog


def _sanitize_preview_text(value: str) -> str:
    sanitized_chars: list[str] = []
    for char in value:
        if char == "\x00":
            continue
        if char in {"\n", "\r", "\t"} or char.isprintable():
            sanitized_chars.append(char)
        else:
            sanitized_chars.append("\uFFFD")
    return "".join(sanitized_chars)


def _build_body_preview(
    *,
    response_body: bytes,
    response_content_type: str | None,
    preview_bytes: int,
) -> str:
    preview_slice = response_body[:preview_bytes]
    content_type = (response_content_type or "").casefold()
    is_textual = any(token in content_type for token in ("text/", "json", "xml", "javascript", "html"))
    if not is_textual:
        return preview_slice.hex()
    decoded = preview_slice.decode("utf-8", errors="replace")
    return _sanitize_preview_text(decoded)


class SourceFetchLogService:
    def __init__(self, *, preview_bytes: int = 4096) -> None:
        self.preview_bytes = preview_bytes

    async def persist(
        self,
        session: AsyncSession,
        *,
        source_name: str,
        fetch_mode: str,
        request_method: str,
        request_url: str,
        response_status: int | None,
        response_headers: dict[str, str] | None,
        response_body: bytes | None,
        response_content_type: str | None,
        latency_ms: int | None,
        error_class: str | None = None,
        fetched_at: datetime | None = None,
    ) -> StyleSourceFetchLog:
        body_hash = None
        body_preview = None
        response_size_bytes = None

        if response_body is not None:
            response_size_bytes = len(response_body)
            body_hash = hashlib.sha256(response_body).hexdigest()
            body_preview = _build_body_preview(
                response_body=response_body,
                response_content_type=response_content_type,
                preview_bytes=self.preview_bytes,
            )

        record = StyleSourceFetchLog(
            source_name=source_name,
            fetch_mode=fetch_mode,
            request_method=request_method.upper(),
            request_url=request_url,
            response_status=response_status,
            response_headers_json=response_headers,
            response_size_bytes=response_size_bytes,
            response_content_type=response_content_type,
            response_body_hash=body_hash,
            response_body_preview=body_preview,
            latency_ms=latency_ms,
            error_class=error_class,
            fetched_at=fetched_at or datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        return record
