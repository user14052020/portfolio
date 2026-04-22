from __future__ import annotations

import hmac
from hashlib import sha256
from typing import TYPE_CHECKING, Protocol

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from app.services.client_request_meta import ClientRequestMeta


class RuntimeSubjectResolverPort(Protocol):
    def resolve_anonymous_subject_id(
        self,
        *,
        session_id: str | None,
        request_meta: ClientRequestMeta | None,
    ) -> str: ...


class RuntimeSubjectResolver:
    def __init__(self, *, settings: Settings | None = None) -> None:
        self.settings = settings

    def resolve_anonymous_subject_id(
        self,
        *,
        session_id: str | None,
        request_meta: ClientRequestMeta | None,
    ) -> str:
        client_key = self._client_key(request_meta)
        if client_key is not None:
            return f"anonymous:{self._hash(client_key)}"

        cleaned_session_id = self._optional_text(session_id)
        if cleaned_session_id is None:
            raise ValueError(
                "Anonymous runtime requests must include session_id or server-resolved client metadata."
            )
        return f"session:{cleaned_session_id}"

    def _client_key(self, request_meta: ClientRequestMeta | None) -> str | None:
        if request_meta is None:
            return None
        client_ip = self._optional_text(request_meta.client_ip)
        if client_ip is None:
            return None
        client_user_agent = self._optional_text(getattr(request_meta, "client_user_agent", None))
        if client_user_agent is None:
            return f"ip:{client_ip.casefold()}"
        return f"ip:{client_ip.casefold()}|ua:{client_user_agent.casefold()}"

    def _hash(self, value: str) -> str:
        settings = self.settings or get_settings()
        digest = hmac.new(
            str(settings.secret_key).encode("utf-8"),
            value.encode("utf-8"),
            sha256,
        ).hexdigest()
        return digest[:32]

    def _optional_text(self, value: object) -> str | None:
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None


runtime_subject_resolver = RuntimeSubjectResolver()
