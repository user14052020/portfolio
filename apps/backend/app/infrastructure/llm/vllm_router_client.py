from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.application.stylist_chat.contracts.ports import (
    ConversationRouterClient,
    RouterClientError,
    RouterClientOutput,
    RouterClientTransportError,
)
from app.core.config import get_settings
from app.domain.routing import ROUTING_MODES, RoutingInput

from .router_prompt_template_loader import build_router_user_prompt, load_router_system_prompt


class VllmRouterClient(ConversationRouterClient):
    ROUTER_MAX_TOKENS = 220
    ROUTER_TEMPERATURE = 0.0
    ROUTER_TIMEOUT_CAP_SECONDS = 18.0
    ROUTER_CONNECT_TIMEOUT_SECONDS = 3.0
    ROUTER_WRITE_TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        settings = None
        if base_url is None or model is None or api_key is None or timeout_seconds is None:
            settings = get_settings()

        self.base_url = (base_url or settings.vllm_base_url).rstrip("/")
        self.model = model or settings.vllm_model
        self.api_key = api_key if api_key is not None else settings.vllm_api_key
        self.timeout_seconds = (
            max(float(timeout_seconds), 1.0)
            if timeout_seconds is not None
            else min(max(float(settings.vllm_timeout_seconds), 1.0), self.ROUTER_TIMEOUT_CAP_SECONDS)
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=2),
        retry=retry_if_exception_type(RouterClientTransportError),
        reraise=True,
    )
    async def route(self, *, routing_input: RoutingInput) -> RouterClientOutput:
        payload = self._build_payload(routing_input=routing_input)
        data = await self._post_chat_completion(payload=payload)
        content = self._extract_content(data)
        return RouterClientOutput(
            payload=self._parse_json_object(content),
            provider=self.model,
            raw_content=content,
        )

    def _build_payload(self, *, routing_input: RoutingInput) -> dict[str, Any]:
        allowed_modes = routing_input.allowed_modes or list(ROUTING_MODES)
        normalized_modes = [mode.value if hasattr(mode, "value") else str(mode) for mode in allowed_modes]
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": load_router_system_prompt(allowed_modes=normalized_modes),
                },
                {
                    "role": "user",
                    "content": build_router_user_prompt(routing_input=routing_input),
                },
            ],
            "temperature": self.ROUTER_TEMPERATURE,
            "max_tokens": self.ROUTER_MAX_TOKENS,
        }

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
            raise RouterClientTransportError("vLLM router request timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = self._extract_http_error_detail(exc.response)
            if exc.response.status_code >= 500 or exc.response.status_code == 429:
                raise RouterClientTransportError(f"vLLM router request failed: {detail}") from exc
            raise RouterClientError(f"vLLM router request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise RouterClientTransportError("vLLM router request failed") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RouterClientError("vLLM router response was not valid JSON") from exc

    def _build_timeout(self) -> httpx.Timeout:
        connect_timeout = min(self.ROUTER_CONNECT_TIMEOUT_SECONDS, self.timeout_seconds)
        write_timeout = min(self.ROUTER_WRITE_TIMEOUT_SECONDS, self.timeout_seconds)
        return httpx.Timeout(
            timeout=self.timeout_seconds,
            connect=connect_timeout,
            read=self.timeout_seconds,
            write=write_timeout,
            pool=connect_timeout,
        )

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RouterClientError("vLLM router response did not include choices")

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

        raise RouterClientError("vLLM router response did not include textual content")

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
                raise RouterClientError("vLLM router response was not valid JSON") from None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise RouterClientError("vLLM router response JSON could not be parsed") from exc

        if not isinstance(parsed, dict):
            raise RouterClientError("vLLM router response JSON must be an object")
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
