from __future__ import annotations

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import (
    ConversationRouterClient,
    ConversationRouterPort,
    ConversationRoutingResult,
    RouterClientError,
    RouterClientTransportError,
)
from app.domain.chat_context import ChatModeContext
from app.domain.routing import RouterFailureReason

from .fallback_router_policy import FallbackRouterPolicy
from .routing_context_builder import RoutingContextBuilder
from .routing_decision_validator import RoutingDecisionValidator


class ConversationRouter(ConversationRouterPort):
    def __init__(
        self,
        *,
        router_client: ConversationRouterClient,
        routing_context_builder: RoutingContextBuilder | None = None,
        decision_validator: RoutingDecisionValidator | None = None,
        fallback_policy: FallbackRouterPolicy | None = None,
    ) -> None:
        self.router_client = router_client
        self.routing_context_builder = routing_context_builder or RoutingContextBuilder()
        self.fallback_policy = fallback_policy or FallbackRouterPolicy()
        self.decision_validator = decision_validator or RoutingDecisionValidator(
            fallback_policy=self.fallback_policy,
        )

    async def route(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> ConversationRoutingResult:
        routing_context = self.routing_context_builder.build_context(command=command, context=context)
        routing_input = self.routing_context_builder.build_input(command=command, context=context)
        short_circuit = self._short_circuit_fallback(
            routing_input=routing_input,
            routing_context=routing_context,
        )
        if short_circuit is not None:
            return short_circuit

        try:
            client_output = await self.router_client.route(routing_input=routing_input)
        except RouterClientError as exc:
            return self._fallback_from_router_error(
                command=command,
                context=context,
                error=exc,
            )

        validation = self.decision_validator.validate(
            raw_payload=client_output.payload,
            routing_input=routing_input,
        )
        return ConversationRoutingResult(
            decision=validation.decision,
            routing_input=routing_input,
            routing_context=routing_context,
            provider=client_output.provider,
            raw_content=client_output.raw_content,
            normalized_payload=validation.normalized_payload,
            validation_errors=validation.validation_errors,
            stripped_fields=validation.stripped_fields,
            used_fallback=validation.used_fallback,
            failure_reason=validation.failure_reason,
            fallback_rule=validation.fallback_rule,
        )

    def _fallback_from_router_error(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
        error: RouterClientError,
    ) -> ConversationRoutingResult:
        routing_context = self.routing_context_builder.build_context(command=command, context=context)
        routing_input = self.routing_context_builder.build_input(command=command, context=context)
        failure_reason = self._map_failure_reason(error)
        fallback = self.fallback_policy.resolve(
            routing_input=routing_input,
            failure_reason=failure_reason,
        )
        return ConversationRoutingResult(
            decision=fallback.decision,
            routing_input=routing_input,
            routing_context=routing_context,
            provider="fallback_router_policy",
            raw_content="",
            normalized_payload={},
            validation_errors=[str(error)] if str(error) else [],
            stripped_fields=[],
            used_fallback=True,
            failure_reason=failure_reason,
            fallback_rule=fallback.matched_rule,
        )

    def _short_circuit_fallback(
        self,
        *,
        routing_input,
        routing_context,
    ) -> ConversationRoutingResult | None:
        fallback = self.fallback_policy.resolve(routing_input=routing_input)
        if (
            routing_input.last_ui_action != "try_other_style"
            and fallback.matched_rule != "clarification_flow_general_pivot"
        ):
            return None
        return ConversationRoutingResult(
            decision=fallback.decision,
            routing_input=routing_input,
            routing_context=routing_context,
            provider="fallback_router_policy",
            raw_content="",
            normalized_payload={},
            validation_errors=[],
            stripped_fields=[],
            used_fallback=True,
            failure_reason=fallback.failure_reason,
            fallback_rule=fallback.matched_rule,
        )

    def _map_failure_reason(self, error: RouterClientError) -> RouterFailureReason:
        message = str(error).strip().lower()
        if isinstance(error, RouterClientTransportError):
            if "timed out" in message or "timeout" in message:
                return RouterFailureReason.TIMEOUT
            return RouterFailureReason.TRANSPORT_ERROR
        if "empty" in message:
            return RouterFailureReason.EMPTY_OUTPUT
        if "json" in message or "content" in message or "object" in message:
            return RouterFailureReason.MALFORMED_OUTPUT
        return RouterFailureReason.UNKNOWN
