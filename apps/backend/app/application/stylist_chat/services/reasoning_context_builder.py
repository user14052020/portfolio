from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import KnowledgeResult
from app.domain.chat_context import ChatModeContext, OccasionContext


class ReasoningContextBuilder:
    def build(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        auto_generate: bool,
        style_seed: dict[str, str] | None,
        previous_style_directions: list[dict[str, str]],
        occasion_context: OccasionContext | None,
        knowledge_result: KnowledgeResult,
        anti_repeat_constraints: dict[str, list[str]] | None,
        structured_outfit_brief: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        profile_context = command.profile_context
        return {
            "locale": command.locale,
            "user_message": command.normalized_message(),
            "uploaded_asset_name": self.asset_name(command.asset_metadata),
            "asset_metadata": command.asset_metadata or None,
            "body_height_cm": self._coerce_int(profile_context.get("height_cm")),
            "body_weight_kg": self._coerce_int(profile_context.get("weight_kg")),
            "auto_generate": auto_generate,
            "conversation_history": self.build_conversation_history(
                context=context,
                fallback_messages=command.fallback_history,
            ),
            "profile_context": profile_context,
            "session_intent": context.active_mode.value,
            "style_seed": style_seed,
            "previous_style_directions": previous_style_directions,
            "occasion_context": occasion_context.model_dump(exclude_none=True) if occasion_context is not None else None,
            "anchor_garment": context.anchor_garment.model_dump(exclude_none=True) if context.anchor_garment else None,
            "structured_outfit_brief": structured_outfit_brief,
            "garment_outfit_brief": structured_outfit_brief,
            "style_exploration_brief": (
                structured_outfit_brief
                if isinstance(structured_outfit_brief, dict)
                and str(structured_outfit_brief.get("brief_type") or "").strip() == "style_exploration"
                else None
            ),
            "knowledge_items": [item.text for item in knowledge_result.items],
            "knowledge_query": knowledge_result.query,
            "anti_repeat_constraints": anti_repeat_constraints or {},
            "last_generation_prompt": context.last_generation_prompt,
            "last_generated_outfit_summary": context.last_generated_outfit_summary,
            "current_style_name": context.current_style_name,
            "current_style_id": context.current_style_id,
        }

    def build_occasion_extraction_history(
        self,
        *,
        context: ChatModeContext,
        command: ChatCommand,
    ) -> list[dict[str, str]]:
        return self.build_conversation_history(
            context=context,
            fallback_messages=command.fallback_history,
            limit=6,
        )

    def build_conversation_history(
        self,
        *,
        context: ChatModeContext,
        fallback_messages: list[dict[str, str]],
        limit: int = 6,
    ) -> list[dict[str, str]]:
        history: list[dict[str, str]] = []
        if context.conversation_memory:
            for memory_item in context.conversation_memory[-limit:]:
                if not memory_item.content.strip():
                    continue
                history.append({"role": memory_item.role, "content": memory_item.content.strip()[:280]})
            return history

        for message in fallback_messages[-limit:]:
            content = message.get("content", "") if isinstance(message, dict) else ""
            if not content.strip():
                continue
            role_value = message.get("role", "user") if isinstance(message, dict) else "user"
            if role_value not in {"user", "assistant", "system"}:
                role_value = "user"
            history.append({"role": role_value, "content": content.strip()[:280]})
        return history

    def build_knowledge_query(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        mode: str,
    ) -> dict[str, Any]:
        return {
            "mode": mode,
            "message": command.normalized_message(),
            "current_style_name": context.current_style_name,
            "anchor_garment": context.anchor_garment.model_dump(exclude_none=True) if context.anchor_garment else None,
            "occasion_context": context.occasion_context.model_dump(exclude_none=True) if context.occasion_context else None,
        }

    def _coerce_int(self, value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    def asset_name(self, asset_metadata: dict[str, Any]) -> str | None:
        raw_value = asset_metadata.get("original_filename")
        if not isinstance(raw_value, str):
            return None
        cleaned = raw_value.strip()
        return cleaned or None
