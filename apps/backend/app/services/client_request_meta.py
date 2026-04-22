from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True, slots=True)
class ClientRequestMeta:
    client_ip: str | None = None
    client_user_agent: str | None = None
    request_origin: str | None = None

    def model_fields(self) -> dict[str, str | None]:
        return {
            "client_ip": self.client_ip,
            "client_user_agent": self.client_user_agent,
            "request_origin": self.request_origin,
        }


class ClientRequestMetaResolver:
    IP_MAX_LENGTH = 128
    USER_AGENT_MAX_LENGTH = 2048
    ORIGIN_MAX_LENGTH = 512

    def resolve(self, request: Request) -> ClientRequestMeta:
        headers = request.headers
        forwarded_for = self._first_forwarded_for(headers.get("x-forwarded-for"))
        real_ip = self._clean_text(headers.get("x-real-ip"), max_length=self.IP_MAX_LENGTH)
        fallback_ip = self._request_client_host(request)

        return ClientRequestMeta(
            client_ip=forwarded_for or real_ip or fallback_ip,
            client_user_agent=self._clean_text(headers.get("user-agent"), max_length=self.USER_AGENT_MAX_LENGTH),
            request_origin=self._clean_text(
                headers.get("origin") or headers.get("referer"),
                max_length=self.ORIGIN_MAX_LENGTH,
            ),
        )

    def _first_forwarded_for(self, value: str | None) -> str | None:
        if not value:
            return None
        for item in value.split(","):
            cleaned = self._clean_text(item, max_length=self.IP_MAX_LENGTH)
            if cleaned:
                return cleaned
        return None

    def _request_client_host(self, request: Request) -> str | None:
        client = request.client
        if client is None:
            return None
        return self._clean_text(client.host, max_length=self.IP_MAX_LENGTH)

    def _clean_text(self, value: str | None, *, max_length: int) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().strip('"').strip("'")
        if not cleaned or cleaned.lower() == "unknown":
            return None
        return cleaned[:max_length]


client_request_meta_resolver = ClientRequestMetaResolver()
