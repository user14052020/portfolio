from app.application.reasoning.contracts import VoiceRuntimeSettingsProvider
from app.domain.reasoning import VoiceContext, VoiceRuntimeFlags, VoiceToneDecision


class DefaultVoiceTonePolicy:
    def __init__(
        self,
        *,
        voice_runtime_flags: VoiceRuntimeFlags | None = None,
        voice_runtime_settings_provider: VoiceRuntimeSettingsProvider | None = None,
    ) -> None:
        self._voice_runtime_flags = voice_runtime_flags or VoiceRuntimeFlags()
        self._voice_runtime_settings_provider = voice_runtime_settings_provider

    async def resolve(self, context: VoiceContext) -> VoiceToneDecision:
        runtime_flags = await self._resolved_runtime_flags()
        if context.response_type == "clarification" or context.mode == "clarification_only":
            return VoiceToneDecision(
                base_tone="smart_stylist",
                use_historian_layer=False,
                use_color_poetics_layer=False,
                brevity_level="light",
                expressive_density="minimal",
                cta_style=None,
            )

        brevity_level = self._brevity_level(context, runtime_flags=runtime_flags)
        return VoiceToneDecision(
            base_tone="smart_stylist",
            use_historian_layer=self._use_historian_layer(
                context,
                brevity_level=brevity_level,
                runtime_flags=runtime_flags,
            ),
            use_color_poetics_layer=self._use_color_poetics_layer(
                context,
                brevity_level=brevity_level,
                runtime_flags=runtime_flags,
            ),
            brevity_level=brevity_level,
            expressive_density=self._expressive_density(context, brevity_level=brevity_level),
            cta_style=self._cta_style(
                context,
                brevity_level=brevity_level,
                runtime_flags=runtime_flags,
            ),
        )

    async def _resolved_runtime_flags(self) -> VoiceRuntimeFlags:
        if self._voice_runtime_settings_provider is None:
            return self._voice_runtime_flags
        return await self._voice_runtime_settings_provider.get_runtime_flags()

    def _brevity_level(self, context: VoiceContext, *, runtime_flags: VoiceRuntimeFlags) -> str:
        if not runtime_flags.deep_mode_enabled:
            return "light" if context.should_be_brief or context.desired_depth == "light" else "normal"
        if context.should_be_brief or context.desired_depth == "light":
            return "light"
        if context.desired_depth == "deep":
            return "deep"
        if context.mode == "general_advice" and context.knowledge_density == "low":
            return "light"
        return "normal"

    def _use_historian_layer(
        self,
        context: VoiceContext,
        *,
        brevity_level: str,
        runtime_flags: VoiceRuntimeFlags,
    ) -> bool:
        if (
            not runtime_flags.historian_enabled
            or not runtime_flags.deep_mode_enabled
            or not context.can_use_historical_layer
            or brevity_level == "light"
        ):
            return False
        if context.mode == "style_exploration":
            return context.desired_depth == "deep" or context.knowledge_density == "high"
        if context.mode == "occasion_outfit":
            return context.desired_depth == "deep" and context.knowledge_density != "low"
        return False

    def _use_color_poetics_layer(
        self,
        context: VoiceContext,
        *,
        brevity_level: str,
        runtime_flags: VoiceRuntimeFlags,
    ) -> bool:
        if (
            not runtime_flags.color_poetics_enabled
            or not runtime_flags.deep_mode_enabled
            or not context.can_use_color_poetics
            or brevity_level == "light"
        ):
            return False
        if context.mode == "style_exploration":
            return context.desired_depth == "deep" or context.knowledge_density == "high"
        if context.mode == "occasion_outfit":
            return context.desired_depth == "deep"
        return False

    def _expressive_density(self, context: VoiceContext, *, brevity_level: str) -> str:
        if brevity_level == "light":
            return "minimal" if context.response_type == "clarification" else "restrained"
        if (
            context.mode == "style_exploration"
            and context.desired_depth == "deep"
            and context.knowledge_density in {"medium", "high"}
        ):
            return "rich_but_controlled"
        return "balanced"

    def _cta_style(
        self,
        context: VoiceContext,
        *,
        brevity_level: str,
        runtime_flags: VoiceRuntimeFlags,
    ) -> str | None:
        if not context.can_offer_visual_cta or context.response_type == "clarification":
            return None
        if context.mode == "style_exploration" and brevity_level == "deep":
            return (
                "editorial_soft_experimental"
                if runtime_flags.cta_experimental_copy_enabled
                else "editorial_soft"
            )
        if brevity_level == "light":
            return "neutral"
        return "soft"
