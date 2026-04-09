import json
from dataclasses import dataclass
from typing import Any, Literal

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.services.stylist_prompt_policy import build_stylist_system_prompt, build_stylist_user_prompt

StylistRoute = Literal["text_only", "text_and_generation", "text_and_catalog"]
StylistIntent = Literal["general_advice", "garment_matching", "style_exploration", "occasion_outfit"]

ALLOWED_ROUTES: set[str] = {"text_only", "text_and_generation", "text_and_catalog"}
ALLOWED_SESSION_INTENTS: set[str] = {"general_advice", "garment_matching", "style_exploration", "occasion_outfit"}


class VLLMClientError(RuntimeError):
    pass


class VLLMRetryableError(VLLMClientError):
    pass


class VLLMTransportError(VLLMRetryableError):
    pass


class VLLMResponseError(VLLMClientError):
    pass


class VLLMContextLimitError(VLLMResponseError):
    pass


@dataclass
class StylistLLMResult:
    reply_text: str
    image_brief_en: str
    route: StylistRoute
    model: str
    raw_content: str


@dataclass
class StylistIntentResult:
    session_intent: StylistIntent
    requires_occasion_clarification: bool
    model: str
    raw_content: str


@dataclass
class OccasionSlotResult:
    event_type: str | None
    venue: str | None
    dress_code: str | None
    time_of_day: str | None
    season_or_weather: str | None
    desired_impression: str | None
    model: str
    raw_content: str


@dataclass
class GarmentIntentResult:
    has_specific_garment: bool
    garment_description: str | None
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
        retry=retry_if_exception_type(VLLMRetryableError),
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
        session_intent: str,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, str]],
        occasion_context: dict[str, str] | None,
    ) -> StylistLLMResult:
        last_context_error: VLLMContextLimitError | None = None
        for history_limit, max_chars, max_tokens in self._generation_budget_variants():
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
                            conversation_history=self._compact_conversation_history(
                                conversation_history,
                                limit=history_limit,
                                max_chars=max_chars,
                            ),
                            profile_context=profile_context,
                            session_intent=session_intent,
                            style_seed=style_seed,
                            previous_style_directions=previous_style_directions,
                            occasion_context=occasion_context,
                        ),
                    },
                ],
                "temperature": self.settings.vllm_temperature,
                "max_tokens": max_tokens,
            }

            try:
                data = await self._post_chat_completion(payload=payload, purpose="generation")
                break
            except VLLMContextLimitError as exc:
                last_context_error = exc
                continue
        else:
            if last_context_error is not None:
                raise last_context_error
            raise VLLMResponseError("vLLM generation could not fit the prompt into context")

        content = self._extract_content(data)
        parsed = self._parse_json_object(content)

        reply_text = str(parsed.get("reply_text", "")).strip()
        image_brief_en = str(parsed.get("image_brief_en", "")).strip()
        route = str(parsed.get("route", "text_only")).strip().lower()

        if not reply_text:
            raise VLLMResponseError("vLLM response missed required fields")
        if route not in ALLOWED_ROUTES:
            route = "text_only"
        self._validate_language_fields(
            locale=locale,
            reply_text=reply_text,
            image_brief_en=image_brief_en,
            route=route,
        )

        return StylistLLMResult(
            reply_text=reply_text,
            image_brief_en=image_brief_en,
            route=route,
            model=self.model,
            raw_content=content,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(VLLMRetryableError),
        reraise=True,
    )
    async def classify_stylist_intent(
        self,
        *,
        user_message: str,
        uploaded_asset_name: str | None,
        conversation_history: list[dict[str, str]],
        latest_assistant_payload: dict[str, Any] | None,
        session_state: dict[str, Any] | None,
    ) -> StylistIntentResult:
        system_prompt = (
            "You are a routing layer for a fashion stylist assistant. "
            "Return strict JSON only with keys: session_intent, requires_occasion_clarification. "
            "Allowed session_intent values: general_advice, garment_matching, style_exploration, occasion_outfit. "
            "Choose garment_matching when the user wants to build a look around a specific garment or photo. "
            "Choose style_exploration when the user wants a new, different, or alternative style direction. "
            "Choose occasion_outfit when the user wants help choosing what to wear for an event, occasion, outing, or dress code. "
            "Choose general_advice for everything else, including explanations, terminology, follow-up questions, and normal conversation inside a stylist context. "
            "Set requires_occasion_clarification to true only when session_intent is occasion_outfit and the event is still generic or unspecified. "
            "If session_state shows an active flow with missing slots or missing garment/profile details, preserve that flow unless the new message clearly starts a different one. "
            "If recent context shows an unfinished routed flow, continue it only when the new message clearly fits that same flow. "
            "Never output markdown."
        )
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "uploaded_asset_name": uploaded_asset_name,
                "conversation_history": self._compact_conversation_history(
                    conversation_history,
                    limit=5,
                    max_chars=180,
                ),
                "latest_assistant_payload": latest_assistant_payload,
                "session_state": session_state,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 120,
        }

        data = await self._post_chat_completion(payload=payload, purpose="routing")
        content = self._extract_content(data)
        parsed = self._parse_json_object(content)
        session_intent = str(parsed.get("session_intent", "general_advice")).strip()
        if session_intent not in ALLOWED_SESSION_INTENTS:
            session_intent = "general_advice"

        requires_occasion_clarification = bool(parsed.get("requires_occasion_clarification"))
        if session_intent != "occasion_outfit":
            requires_occasion_clarification = False

        return StylistIntentResult(
            session_intent=session_intent,
            requires_occasion_clarification=requires_occasion_clarification,
            model=self.model,
            raw_content=content,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(VLLMRetryableError),
        reraise=True,
    )
    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionSlotResult:
        system_prompt = (
            "You extract structured event styling context for a fashion assistant. "
            "Return strict JSON only with keys: event_type, venue, dress_code, time_of_day, season_or_weather, desired_impression. "
            "Use null when a field is missing. "
            "event_type must capture the actual occasion, for example wedding, dinner, office party, date, theater, birthday, conference, funeral, club night. "
            "Do not invent details that are not present or clearly implied."
        )
        user_prompt = json.dumps(
            {
                "locale": locale,
                "user_message": user_message,
                "conversation_history": self._compact_conversation_history(
                    conversation_history,
                    limit=4,
                    max_chars=160,
                ),
                "existing_slots": existing_slots,
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 160,
        }

        data = await self._post_chat_completion(payload=payload, purpose="routing")
        content = self._extract_content(data)
        parsed = self._parse_json_object(content)
        return OccasionSlotResult(
            event_type=self._optional_text(parsed.get("event_type")),
            venue=self._optional_text(parsed.get("venue")),
            dress_code=self._optional_text(parsed.get("dress_code")),
            time_of_day=self._optional_text(parsed.get("time_of_day")),
            season_or_weather=self._optional_text(parsed.get("season_or_weather")),
            desired_impression=self._optional_text(parsed.get("desired_impression")),
            model=self.model,
            raw_content=content,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type(VLLMRetryableError),
        reraise=True,
    )
    async def analyze_garment_request(
        self,
        *,
        user_message: str,
        conversation_history: list[dict[str, str]],
    ) -> GarmentIntentResult:
        system_prompt = (
            "You validate whether a user has already described a specific garment for outfit matching. "
            "Return strict JSON only with keys: has_specific_garment, garment_description. "
            "has_specific_garment must be true only if the user already provided a recognizable garment or accessory anchor. "
            "garment_description should be a short plain-text summary of that anchor item, or null when absent."
        )
        user_prompt = json.dumps(
            {
                "user_message": user_message,
                "conversation_history": self._compact_conversation_history(
                    conversation_history,
                    limit=4,
                    max_chars=140,
                ),
            },
            ensure_ascii=False,
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "max_tokens": 120,
        }

        data = await self._post_chat_completion(payload=payload, purpose="routing")
        content = self._extract_content(data)
        parsed = self._parse_json_object(content)
        return GarmentIntentResult(
            has_specific_garment=bool(parsed.get("has_specific_garment")),
            garment_description=self._optional_text(parsed.get("garment_description")),
            model=self.model,
            raw_content=content,
        )

    async def _post_chat_completion(
        self,
        *,
        payload: dict[str, Any],
        purpose: Literal["generation", "routing"],
    ) -> dict[str, Any]:
        timeout = self._build_timeout(purpose)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self._build_headers(),
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise VLLMTransportError(f"vLLM {purpose} request timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = self._extract_http_error_detail(exc.response)
            if exc.response.status_code == 400 and self._is_context_limit_error(detail):
                raise VLLMContextLimitError(detail) from exc
            raise VLLMResponseError(f"vLLM {purpose} request failed: {detail}") from exc
        except httpx.HTTPError as exc:
            raise VLLMTransportError(f"vLLM {purpose} request failed") from exc

        return response.json()

    def _build_timeout(self, purpose: Literal["generation", "routing"]) -> httpx.Timeout:
        configured_timeout = max(float(self.settings.vllm_timeout_seconds), 1.0)
        connect_timeout = min(5.0, configured_timeout)
        write_timeout = min(10.0, configured_timeout)
        return httpx.Timeout(
            timeout=configured_timeout,
            connect=connect_timeout,
            read=configured_timeout,
            write=write_timeout,
            pool=connect_timeout,
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

    def _is_context_limit_error(self, detail: str) -> bool:
        lowered = detail.lower()
        return "maximum context length" in lowered or "input_tokens" in lowered

    def _generation_budget_variants(self) -> list[tuple[int, int, int]]:
        configured_max_tokens = max(int(self.settings.vllm_max_tokens), 160)
        variants = [
            (6, 260, min(configured_max_tokens, 420)),
            (4, 180, min(configured_max_tokens, 320)),
            (2, 120, min(configured_max_tokens, 220)),
        ]
        deduplicated: list[tuple[int, int, int]] = []
        seen: set[tuple[int, int, int]] = set()
        for variant in variants:
            if variant not in seen:
                deduplicated.append(variant)
                seen.add(variant)
        return deduplicated

    def _compact_conversation_history(
        self,
        conversation_history: list[dict[str, str]],
        *,
        limit: int,
        max_chars: int,
    ) -> list[dict[str, str]]:
        compacted: list[dict[str, str]] = []
        for message in conversation_history[-limit:]:
            role = str(message.get("role", "user")).strip() or "user"
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            compacted.append({"role": role, "content": content[:max_chars]})
        return compacted

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.settings.vllm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.vllm_api_key}"
        return headers

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        if not cleaned or cleaned.lower() in {"null", "none", "n/a", "unspecified"}:
            return None
        return cleaned

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
        reply_text: str,
        image_brief_en: str,
        route: StylistRoute,
    ) -> None:
        if locale == "ru":
            if not self._looks_russian(reply_text):
                raise VLLMResponseError("reply_text is not valid Russian text")
        else:
            if not self._looks_english(reply_text):
                raise VLLMResponseError("reply_text is not valid English text")

        if self._contains_cjk(reply_text):
            raise VLLMResponseError("reply_text contains CJK characters")

        if route != "text_only" and not image_brief_en:
            raise VLLMResponseError("image_brief_en is required for generation routes")
        if image_brief_en and not self._looks_english(image_brief_en):
            raise VLLMResponseError("image_brief_en is not valid English text")

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
