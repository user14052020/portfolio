from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings


class OpenAIChatGptClientError(RuntimeError):
    pass


class OpenAIChatGptConfigurationError(OpenAIChatGptClientError):
    pass


class OpenAIChatGptTransportError(OpenAIChatGptClientError):
    pass


class OpenAIChatGptResponseError(OpenAIChatGptClientError):
    def __init__(self, message: str, *, raw_content: str | None = None) -> None:
        super().__init__(message)
        self.raw_content = raw_content


@dataclass(frozen=True)
class ChatGptStructuredCompletion:
    payload: dict[str, Any]
    provider: str
    raw_content: str


class OpenAIChatGptClient:
    DEFAULT_MAX_TOKENS = 2200
    DEFAULT_TEMPERATURE = 0.0
    CONNECT_TIMEOUT_SECONDS = 5.0
    WRITE_TIMEOUT_SECONDS = 10.0

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = None
        if base_url is None or api_key is None or model is None or timeout_seconds is None:
            settings = get_settings()

        self.base_url = (base_url or settings.openai_base_url).rstrip("/")
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.openai_model
        self.timeout_seconds = max(float(timeout_seconds or settings.openai_timeout_seconds), 1.0)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(OpenAIChatGptTransportError),
        reraise=True,
    )
    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> ChatGptStructuredCompletion:
        if not self.api_key:
            raise OpenAIChatGptConfigurationError("OPENAI_API_KEY is not configured for style enrichment")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.DEFAULT_TEMPERATURE if temperature is None else float(temperature),
            "max_tokens": self.DEFAULT_MAX_TOKENS if max_tokens is None else int(max_tokens),
            "response_format": {"type": "json_object"},
        }

        data = await self._post_chat_completion(payload=payload)
        content = self._extract_content(data)
        return ChatGptStructuredCompletion(
            payload=self._parse_json_object(content),
            provider=str(data.get("model") or self.model),
            raw_content=content,
        )

    async def _post_chat_completion(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self._build_timeout()) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise OpenAIChatGptTransportError("OpenAI enrichment request timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = self._extract_http_error_detail(exc.response)
            if exc.response.status_code >= 500 or exc.response.status_code == 429:
                raise OpenAIChatGptTransportError(f"OpenAI enrichment request failed: {detail}") from exc
            raise OpenAIChatGptClientError(f"OpenAI enrichment request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise OpenAIChatGptTransportError("OpenAI enrichment request failed") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise OpenAIChatGptResponseError("OpenAI enrichment response was not valid JSON") from exc

    def _build_timeout(self) -> httpx.Timeout:
        connect_timeout = min(self.CONNECT_TIMEOUT_SECONDS, self.timeout_seconds)
        write_timeout = min(self.WRITE_TIMEOUT_SECONDS, self.timeout_seconds)
        return httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=connect_timeout,
            read=self.timeout_seconds,
            write=write_timeout,
            pool=connect_timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAIChatGptResponseError("OpenAI enrichment response did not include choices")

        message = choices[0].get("message", {})
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_value = item.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            if text_parts:
                return "".join(text_parts)

        raise OpenAIChatGptResponseError("OpenAI enrichment response did not include textual content")

    def _parse_json_object(self, raw_content: str) -> dict[str, Any]:
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`").strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise OpenAIChatGptResponseError(
                    "OpenAI enrichment response was not valid JSON",
                    raw_content=raw_content,
                ) from None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise OpenAIChatGptResponseError(
                    "OpenAI enrichment response JSON could not be parsed",
                    raw_content=raw_content,
                ) from exc

        if not isinstance(parsed, dict):
            raise OpenAIChatGptResponseError(
                "OpenAI enrichment response JSON must be an object",
                raw_content=raw_content,
            )
        return parsed

    def _extract_http_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text.strip() or f"HTTP {response.status_code}"

        if isinstance(payload, dict):
            for key in ("detail", "message", "error"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
                if isinstance(value, dict):
                    nested_message = value.get("message")
                    if isinstance(nested_message, str) and nested_message.strip():
                        return nested_message.strip()

        return response.text.strip() or f"HTTP {response.status_code}"
