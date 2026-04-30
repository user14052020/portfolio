import json
from typing import Any

import httpx

from app.application.reasoning.contracts import VoiceCompositionClient
from app.core.config import get_settings
from app.domain.reasoning import VoiceCompositionDraft, VoiceContext, VoicePrompt


class VoiceCompositionClientError(RuntimeError):
    pass


class OpenAICompatibleVoiceCompositionClient(VoiceCompositionClient):
    def __init__(self) -> None:
        self._settings = get_settings()
        self._base_url = self._settings.vllm_base_url.rstrip("/")
        self._model = self._settings.vllm_model

    async def compose(
        self,
        *,
        prompt: VoicePrompt,
        context: VoiceContext,
    ) -> VoiceCompositionDraft:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt.system_prompt},
                {"role": "user", "content": prompt.user_prompt},
            ],
            "temperature": self._settings.vllm_temperature,
            "max_tokens": self._max_tokens_for(context),
        }
        timeout = self._build_timeout()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                    headers=self._headers(),
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VoiceCompositionClientError("voice composition request failed") from exc

        content = self._extract_content(response.json())
        parsed = self._parse_json_object(content)
        final_text = str(parsed.get("final_text", "")).strip()
        if not final_text:
            raise VoiceCompositionClientError("voice composition returned empty final_text")

        cta_text = parsed.get("cta_text")
        cta_value = str(cta_text).strip() if isinstance(cta_text, str) and cta_text.strip() else None
        return VoiceCompositionDraft(
            final_text=final_text,
            cta_text=cta_value,
            used_historical_note=bool(parsed.get("used_historical_note")),
            used_color_poetics=bool(parsed.get("used_color_poetics")),
            raw_content=content,
            provider_model=self._model,
        )

    def _max_tokens_for(self, context: VoiceContext) -> int:
        configured = max(int(self._settings.vllm_max_tokens), 160)
        if context.response_type == "clarification" or context.desired_depth == "light":
            return min(configured, 180)
        if context.desired_depth == "deep":
            return min(configured, 320)
        return min(configured, 240)

    def _build_timeout(self) -> httpx.Timeout:
        configured_timeout = max(float(self._settings.vllm_timeout_seconds), 1.0)
        connect_timeout = min(5.0, configured_timeout)
        write_timeout = min(10.0, configured_timeout)
        return httpx.Timeout(
            timeout=configured_timeout,
            connect=connect_timeout,
            read=configured_timeout,
            write=write_timeout,
            pool=connect_timeout,
        )

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self._settings.vllm_api_key:
            headers["Authorization"] = f"Bearer {self._settings.vllm_api_key}"
        return headers

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise VoiceCompositionClientError("voice composition response did not include choices")
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
        raise VoiceCompositionClientError("voice composition response did not include textual content")

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
                raise VoiceCompositionClientError("voice composition response was not valid JSON") from None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise VoiceCompositionClientError("voice composition JSON could not be parsed") from exc

        if not isinstance(parsed, dict):
            raise VoiceCompositionClientError("voice composition JSON must be an object")
        return parsed
