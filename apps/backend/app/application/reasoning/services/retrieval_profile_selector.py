from app.domain.reasoning import SessionStateSnapshot
from app.domain.routing.entities.routing_decision import RoutingDecision
from app.domain.routing.enums.routing_mode import RoutingMode


class DefaultRetrievalProfileSelector:
    def select(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        requested_profile: str | None,
    ) -> str | None:
        explicit_profile = requested_profile.strip() if isinstance(requested_profile, str) else None
        if explicit_profile:
            return explicit_profile

        mode = routing_decision.mode
        if routing_decision.generation_intent and session_state.can_generate_now:
            return "visual_heavy"
        if mode == RoutingMode.OCCASION_OUTFIT:
            return "occasion_focused"
        if (
            mode == RoutingMode.STYLE_EXPLORATION
            or routing_decision.requires_style_retrieval
            or routing_decision.requires_historical_layer
            or routing_decision.requires_stylist_guidance
        ):
            return "style_focused"
        return "light"
