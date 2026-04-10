from typing import Any

from app.application.stylist_chat.contracts.ports import (
    LLMReasoner,
    LLMReasonerContextLimitError,
    LLMReasonerError,
    OccasionExtractionOutput,
    ReasoningOutput,
)

try:
    from app.integrations.vllm import VLLMClient, VLLMClientError, VLLMContextLimitError
except ModuleNotFoundError:
    VLLMClient = None

    class VLLMClientError(RuntimeError):
        pass

    class VLLMContextLimitError(VLLMClientError):
        pass


class _UnavailableVLLMClient:
    async def generate_stylist_response(self, **_: object):
        raise VLLMClientError("vLLM client dependencies are unavailable in this environment")

    async def extract_occasion_slots(self, **_: object):
        raise VLLMClientError("vLLM client dependencies are unavailable in this environment")


class VLLMReasonerAdapter(LLMReasoner):
    def __init__(self) -> None:
        self.client = VLLMClient() if VLLMClient is not None else _UnavailableVLLMClient()

    async def decide(self, *, locale: str, reasoning_input: dict[str, Any]) -> ReasoningOutput:
        try:
            result = await self.client.generate_stylist_response(
                locale=locale,
                user_message=str(reasoning_input.get("user_message") or ""),
                uploaded_asset_name=self._optional_text(reasoning_input.get("uploaded_asset_name")),
                body_height_cm=self._coerce_int(reasoning_input.get("body_height_cm")),
                body_weight_kg=self._coerce_int(reasoning_input.get("body_weight_kg")),
                auto_generate=bool(reasoning_input.get("auto_generate")),
                conversation_history=reasoning_input.get("conversation_history") or [],
                profile_context=reasoning_input.get("profile_context") or {},
                session_intent=str(reasoning_input.get("session_intent") or "general_advice"),
                style_seed=reasoning_input.get("style_seed"),
                previous_style_directions=reasoning_input.get("previous_style_directions") or [],
                occasion_context=reasoning_input.get("occasion_context"),
            )
        except VLLMContextLimitError as exc:
            raise LLMReasonerContextLimitError(str(exc)) from exc
        except VLLMClientError as exc:
            raise LLMReasonerError(str(exc)) from exc
        return ReasoningOutput(
            reply_text=result.reply_text,
            image_brief_en=result.image_brief_en,
            route=result.route,
            provider=getattr(result, "model", "vllm"),
            raw_content=getattr(result, "raw_content", ""),
            reasoning_mode="primary",
        )

    async def extract_occasion_slots(
        self,
        *,
        locale: str,
        user_message: str,
        conversation_history: list[dict[str, str]],
        existing_slots: dict[str, str | None],
    ) -> OccasionExtractionOutput:
        try:
            result = await self.client.extract_occasion_slots(
                locale=locale,
                user_message=user_message,
                conversation_history=conversation_history,
                existing_slots=existing_slots,
            )
        except VLLMClientError as exc:
            raise LLMReasonerError(str(exc)) from exc
        return OccasionExtractionOutput(
            event_type=result.event_type,
            venue=result.venue,
            dress_code=result.dress_code,
            time_of_day=result.time_of_day,
            season_or_weather=result.season_or_weather,
            desired_impression=result.desired_impression,
            provider=getattr(result, "model", "vllm"),
            raw_content=getattr(result, "raw_content", ""),
        )

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None
