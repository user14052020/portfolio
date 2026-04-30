from __future__ import annotations

from app.application.stylist_chat.contracts.command import ChatCommand
from app.domain.chat_context import ChatModeContext, ConversationMemoryItem
from app.domain.chat_modes import ChatMode, ClarificationKind, FlowState
from app.domain.routing import (
    ConversationRouterContext,
    ROUTING_MODES,
    RoutingInput,
    RoutingMessageExcerpt,
    RoutingMode,
)


RECENT_ROUTING_TURNS_LIMIT = 4


class RoutingContextBuilder:
    def build_context(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> ConversationRouterContext:
        return ConversationRouterContext(
            active_mode=self._coerce_mode(context),
            flow_state=context.flow_state.value if context.flow_state else None,
            pending_slots=self._resolve_pending_slots(context=context),
            recent_messages=self._build_recent_messages(
                context=context,
                fallback_messages=command.fallback_history,
            ),
            last_ui_action=self._resolve_last_ui_action(command=command, context=context),
            last_generation_completed=context.flow_state == FlowState.COMPLETED,
            last_visual_cta_offered=bool(
                context.visualization_offer and context.visualization_offer.can_offer_visualization
            ),
            profile_context_present=self._profile_context_present(command=command),
        )

    def build_input(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> RoutingInput:
        router_context = self.build_context(command=command, context=context)
        return RoutingInput(
            user_message=command.normalized_message(),
            active_mode=router_context.active_mode,
            flow_state=router_context.flow_state,
            pending_slots=list(router_context.pending_slots),
            recent_messages=[item.content for item in router_context.recent_messages],
            last_ui_action=router_context.last_ui_action,
            profile_hint_present=router_context.profile_context_present,
            allowed_modes=list(ROUTING_MODES),
        )

    def _build_recent_messages(
        self,
        *,
        context: ChatModeContext,
        fallback_messages: list[dict[str, str]],
    ) -> list[RoutingMessageExcerpt]:
        excerpts: list[RoutingMessageExcerpt] = []
        if context.conversation_memory:
            source_items: list[ConversationMemoryItem] = []
            for item in reversed(context.conversation_memory):
                if item.role in {"user", "assistant"}:
                    source_items.append(item)
                if len(source_items) >= RECENT_ROUTING_TURNS_LIMIT:
                    break
            for item in reversed(source_items):
                excerpt = self._excerpt_from_memory(item)
                if excerpt is not None:
                    excerpts.append(excerpt)
            return excerpts

        for item in fallback_messages[-RECENT_ROUTING_TURNS_LIMIT:]:
            excerpt = self._excerpt_from_fallback(item)
            if excerpt is not None:
                excerpts.append(excerpt)
        return excerpts

    def _excerpt_from_memory(self, item: ConversationMemoryItem) -> RoutingMessageExcerpt | None:
        if item.role not in {"user", "assistant"}:
            return None
        content = item.content.strip()
        if not content:
            return None
        return RoutingMessageExcerpt(role=item.role, content=content[:280])

    def _excerpt_from_fallback(self, item: dict[str, str]) -> RoutingMessageExcerpt | None:
        role = str(item.get("role") or "").strip()
        if role not in {"user", "assistant"}:
            return None
        content = str(item.get("content") or "").strip()
        if not content:
            return None
        return RoutingMessageExcerpt(role=role, content=content[:280])

    def _resolve_pending_slots(self, *, context: ChatModeContext) -> list[str]:
        slots: list[str] = []
        if context.active_mode == ChatMode.GARMENT_MATCHING:
            if context.anchor_garment is None:
                slots.append("anchor_garment")
            else:
                slots.extend(context.anchor_garment.missing_attributes())
        elif context.active_mode == ChatMode.OCCASION_OUTFIT:
            if context.occasion_context is None:
                slots.append("occasion_details")
            else:
                slots.extend(context.occasion_context.missing_core_slots())

        clarification_slot = self._slot_from_clarification_kind(context.clarification_kind)
        if clarification_slot is not None:
            slots.append(clarification_slot)

        flow_slot = self._slot_from_flow_state(context.flow_state)
        if flow_slot is not None:
            slots.append(flow_slot)

        if context.pending_clarification and not slots:
            slots.append("clarification")

        return self._deduplicate(slots)

    def _slot_from_clarification_kind(self, kind: ClarificationKind | None) -> str | None:
        if kind is None:
            return None
        mapping = {
            ClarificationKind.ANCHOR_GARMENT_DESCRIPTION: "anchor_garment",
            ClarificationKind.ANCHOR_GARMENT_MISSING_ATTRIBUTES: "garment_attributes",
            ClarificationKind.OCCASION_EVENT_TYPE: "event_type",
            ClarificationKind.OCCASION_TIME_OF_DAY: "time_of_day",
            ClarificationKind.OCCASION_SEASON: "season",
            ClarificationKind.OCCASION_DRESS_CODE: "dress_code",
            ClarificationKind.OCCASION_DESIRED_IMPRESSION: "desired_impression",
            ClarificationKind.OCCASION_MISSING_MULTIPLE_SLOTS: "occasion_details",
            ClarificationKind.STYLE_PREFERENCE: "style_preference",
            ClarificationKind.GENERAL_FOLLOWUP: "clarification",
        }
        return mapping.get(kind)

    def _slot_from_flow_state(self, state: FlowState | None) -> str | None:
        if state is None:
            return None
        mapping = {
            FlowState.AWAITING_ANCHOR_GARMENT: "anchor_garment",
            FlowState.AWAITING_ANCHOR_GARMENT_CLARIFICATION: "garment_attributes",
            FlowState.AWAITING_OCCASION_DETAILS: "occasion_details",
            FlowState.AWAITING_OCCASION_CLARIFICATION: "occasion_details",
            FlowState.AWAITING_CLARIFICATION: "clarification",
        }
        return mapping.get(state)

    def _resolve_last_ui_action(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> str | None:
        current_action = self._normalize_ui_action(
            source=command.source,
            command_name=command.command_name,
            command_step=command.command_step,
        )
        if current_action is not None:
            return current_action

        if context.command_context is None:
            return None
        source = context.command_context.metadata.get("source")
        normalized_source = source.strip() if isinstance(source, str) else None
        return self._normalize_ui_action(
            source=normalized_source,
            command_name=context.command_context.command_name,
            command_step=context.command_context.command_step,
        )

    def _normalize_ui_action(
        self,
        *,
        source: str | None,
        command_name: str | None,
        command_step: str | None,
    ) -> str | None:
        if source == "quick_action" and command_name == RoutingMode.STYLE_EXPLORATION.value:
            return "try_other_style"
        if source == "visualization_cta" or command_step == "confirm_visualization":
            return "confirm_visualization"
        return None

    def _profile_context_present(self, *, command: ChatCommand) -> bool:
        profile_sources = [
            command.profile_context,
            command.metadata.get("session_profile_context"),
            command.metadata.get("persistent_profile_context"),
            command.metadata.get("profile_recent_updates"),
        ]
        return any(self._profile_source_present(source) for source in profile_sources)

    def _profile_source_present(self, value: object) -> bool:
        if not isinstance(value, dict):
            return False
        return any(self._has_profile_value(item) for item in value.values())

    def _coerce_mode(self, context: ChatModeContext) -> RoutingMode | None:
        raw_value = context.active_mode.value if context.active_mode else None
        if raw_value is None:
            return None
        try:
            return RoutingMode(raw_value)
        except ValueError:
            return None

    def _deduplicate(self, items: list[str]) -> list[str]:
        result: list[str] = []
        for item in items:
            cleaned = item.strip()
            if not cleaned or cleaned in result:
                continue
            result.append(cleaned)
        return result

    def _has_profile_value(self, value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict, tuple, set)):
            return bool(value)
        return True
