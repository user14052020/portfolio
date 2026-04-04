import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.stylist_prompt_policy import build_stylist_system_prompt, build_stylist_user_prompt

StylistRoute = Literal["text_only", "text_and_generation", "text_and_catalog"]

ALLOWED_ROUTES: set[str] = {"text_only", "text_and_generation", "text_and_catalog"}


class VLLMClientError(RuntimeError):
    pass


class VLLMResponseError(VLLMClientError):
    pass


@dataclass
class StylistLLMResult:
    reply_ru: str
    reply_en: str
    route: StylistRoute
    model: str
    raw_content: str


class VLLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.vllm_base_url.rstrip("/")
        self.model = self.settings.vllm_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(VLLMClientError),
        reraise=True,
    )
    async def generate_stylist_response(
        self,
        *,
        locale: str,
        user_message: str,
        uploaded_asset_name: str | None,
        body_height_cm: int | None,
        body_weight_kg: int | None,
        auto_generate: bool,
        conversation_history: list[dict[str, str]],
        profile_context: dict[str, str | int | None],
    ) -> StylistLLMResult:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": build_stylist_system_prompt()},
                {
                    "role": "user",
                    "content": build_stylist_user_prompt(
                        locale=locale,
                        user_message=user_message,
                        uploaded_asset_name=uploaded_asset_name,
                        body_height_cm=body_height_cm,
                        body_weight_kg=body_weight_kg,
                        auto_generate=auto_generate,
                        conversation_history=conversation_history,
                        profile_context=profile_context,
                    ),
                },
            ],
            "temperature": self.settings.vllm_temperature,
            "max_tokens": self.settings.vllm_max_tokens,
        }

        headers: dict[str, str] = {}
        if self.settings.vllm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.vllm_api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.settings.vllm_timeout_seconds) as client:
                response = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise VLLMClientError("vLLM request failed") from exc

        data = response.json()
        content = self._extract_content(data)
        parsed = self._parse_json_object(content)

        reply_ru = str(parsed.get("reply_ru", "")).strip()
        reply_en = str(parsed.get("reply_en", "")).strip()
        route = str(parsed.get("route", "text_only")).strip().lower()

        if not reply_ru or not reply_en:
            raise VLLMResponseError("vLLM response missed required fields")
        self._validate_language_fields(
            locale=locale,
            reply_ru=reply_ru,
            reply_en=reply_en,
        )
        if route not in ALLOWED_ROUTES:
            route = "text_only"

        return StylistLLMResult(
            reply_ru=reply_ru,
            reply_en=reply_en,
            route=route,
            model=self.model,
            raw_content=content,
        )

    def _extract_content(self, payload: dict[str, Any]) -> str:
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise VLLMResponseError("vLLM response did not include choices")

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

        raise VLLMResponseError("vLLM response did not include textual content")

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
                raise VLLMResponseError("vLLM response was not valid JSON") from None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError as exc:
                raise VLLMResponseError("vLLM response JSON could not be parsed") from exc

        if not isinstance(parsed, dict):
            raise VLLMResponseError("vLLM response JSON must be an object")
        return parsed

    def _validate_language_fields(
        self,
        *,
        locale: str,
        reply_ru: str,
        reply_en: str,
    ) -> None:
        if not self._looks_russian(reply_ru):
            raise VLLMResponseError("reply_ru is not valid Russian text")
        if not self._looks_english(reply_en):
            raise VLLMResponseError("reply_en is not valid English text")

        primary_text = reply_ru if locale == "ru" else reply_en
        if self._contains_cjk(primary_text):
            raise VLLMResponseError("primary reply contains CJK characters")

    def _looks_russian(self, text: str) -> bool:
        return self._has_expected_script(text=text, expected="cyrillic")

    def _looks_english(self, text: str) -> bool:
        return self._has_expected_script(text=text, expected="latin")

    def _has_expected_script(self, *, text: str, expected: Literal["cyrillic", "latin"]) -> bool:
        letters = [char for char in text if char.isalpha()]
        if not letters:
            return False

        cyrillic = sum(1 for char in letters if self._is_cyrillic(char))
        latin = sum(1 for char in letters if self._is_latin(char))
        cjk = sum(1 for char in letters if self._is_cjk(char))
        total = len(letters)

        if cjk > 0:
            return False

        if expected == "cyrillic":
            return cyrillic / total >= 0.7 and latin / total <= 0.25
        return latin / total >= 0.7 and cyrillic / total <= 0.25

    def _contains_cjk(self, text: str) -> bool:
        return any(self._is_cjk(char) for char in text)

    def _is_latin(self, char: str) -> bool:
        code = ord(char)
        return 0x0041 <= code <= 0x005A or 0x0061 <= code <= 0x007A

    def _is_cyrillic(self, char: str) -> bool:
        code = ord(char)
        return (
            0x0400 <= code <= 0x04FF
            or 0x0500 <= code <= 0x052F
            or 0x2DE0 <= code <= 0x2DFF
            or 0xA640 <= code <= 0xA69F
        )

    def _is_cjk(self, char: str) -> bool:
        code = ord(char)
        return (
            0x3400 <= code <= 0x4DBF
            or 0x4E00 <= code <= 0x9FFF
            or 0xF900 <= code <= 0xFAFF
        )
