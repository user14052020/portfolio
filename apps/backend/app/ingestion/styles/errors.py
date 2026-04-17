from __future__ import annotations


class StyleIngestionError(RuntimeError):
    """Base runtime error for style ingestion pipeline failures."""


class DonorApiError(StyleIngestionError):
    def __init__(
        self,
        *,
        source_name: str,
        fetch_mode: str,
        request_url: str,
        reason: str,
        status_code: int | None = None,
        detail: str | None = None,
    ) -> None:
        self.source_name = source_name
        self.fetch_mode = fetch_mode
        self.request_url = request_url
        self.reason = reason
        self.status_code = status_code
        self.detail = detail

        parts = [
            f"Donor API request failed for source {source_name!r}",
            f"fetch_mode={fetch_mode!r}",
            f"reason={reason!r}",
            f"request_url={request_url!r}",
        ]
        if status_code is not None:
            parts.append(f"status_code={status_code}")
        if detail:
            parts.append(f"detail={detail}")
        super().__init__(", ".join(parts))


class DonorPayloadError(DonorApiError):
    """Raised when donor API responds, but payload shape is not usable by the pipeline."""
