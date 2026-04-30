from app.application.reasoning.contracts import VoiceRuntimeSettingsProvider
from app.domain.reasoning import (
    FashionReasoningOutput,
    VoiceContext,
    VoicePrompt,
    VoiceRuntimeFlags,
    VoiceToneDecision,
)


class DefaultVoicePromptBuilder:
    def __init__(
        self,
        *,
        voice_runtime_flags: VoiceRuntimeFlags | None = None,
        voice_runtime_settings_provider: VoiceRuntimeSettingsProvider | None = None,
    ) -> None:
        self._voice_runtime_flags = voice_runtime_flags or VoiceRuntimeFlags()
        self._voice_runtime_settings_provider = voice_runtime_settings_provider

    async def build(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
        tone_decision: VoiceToneDecision,
    ) -> VoicePrompt:
        runtime_flags = await self._resolved_runtime_flags()
        layers_requested = ["stylist"]
        if (
            runtime_flags.historian_enabled
            and runtime_flags.deep_mode_enabled
            and tone_decision.use_historian_layer
            and context.can_use_historical_layer
            and reasoning_output.historical_note_candidates
        ):
            layers_requested.append("historian")
        if (
            runtime_flags.color_poetics_enabled
            and runtime_flags.deep_mode_enabled
            and tone_decision.use_color_poetics_layer
            and context.can_use_color_poetics
            and (
                reasoning_output.color_poetic_candidates
                or reasoning_output.composition_theory_candidates
                or reasoning_output.visual_language_points
            )
        ):
            layers_requested.append("color_poetics")

        system_lines = [
            "You are the voice composition layer for a fashion assistant.",
            "Do not invent new fashion logic.",
            "Do not alter the fashion brief, generation constraints, garments, palette, or silhouette.",
            "Phrase only the structured reasoning that is already provided.",
            (
                "Return strict JSON only with keys: "
                "final_text, cta_text, used_historical_note, used_color_poetics."
            ),
            "final_text must contain only the main stylist reply.",
            "Never place CTA wording inside final_text; keep CTA in cta_text only.",
            "Use null for cta_text when no CTA should be shown.",
            f"Reply in locale: {context.locale}.",
            f"Base tone: {tone_decision.base_tone}.",
            f"Brevity level: {self._effective_brevity_level(tone_decision, runtime_flags=runtime_flags)}.",
            f"Expressive density: {tone_decision.expressive_density}.",
            f"Mode: {context.mode}.",
            f"Response type: {context.response_type}.",
        ]
        if context.profile_context_present:
            system_lines.append(
                "The reasoning is already profile-aware. Preserve that personalization without asking for new profile data."
            )
        if "historian" in layers_requested:
            system_lines.append(
                "Historical context may be used only from provided historical candidates and must stay subordinate to practical styling advice."
            )
        if "color_poetics" in layers_requested:
            system_lines.append(
                "Color and form poetics may be used only to clarify existing visual-language reasoning, never as free-form literary invention."
            )
        if context.response_type == "clarification":
            system_lines.append("Keep the response extremely direct and practical.")

        user_lines = [
            "Draft response seed:",
            reasoning_output.text_response,
        ]
        if reasoning_output.clarification_question and context.response_type == "clarification":
            user_lines.extend(
                [
                    "Clarification question:",
                    reasoning_output.clarification_question,
                ]
            )
        self._append_list(user_lines, "Style logic points", reasoning_output.style_logic_points)
        self._append_list(user_lines, "Visual language points", reasoning_output.visual_language_points)
        self._append_list(user_lines, "Styling rule candidates", reasoning_output.styling_rule_candidates)
        if "historian" in layers_requested:
            self._append_list(
                user_lines,
                "Historical note candidates",
                reasoning_output.historical_note_candidates,
            )
            self._append_list(
                user_lines,
                "Editorial context candidates",
                reasoning_output.editorial_context_candidates,
            )
        if "color_poetics" in layers_requested:
            self._append_list(
                user_lines,
                "Color poetic candidates",
                reasoning_output.color_poetic_candidates,
            )
            self._append_list(
                user_lines,
                "Composition theory candidates",
                reasoning_output.composition_theory_candidates,
            )
        if (
            context.can_offer_visual_cta
            and reasoning_output.can_offer_visualization
            and tone_decision.cta_style
            and reasoning_output.suggested_cta
        ):
            user_lines.extend(
                [
                    "CTA guidance:",
                    f"- CTA style: {tone_decision.cta_style}",
                    f"- CTA seed: {reasoning_output.suggested_cta}",
                ]
            )

        observability = {
            "voice_prompt_mode": context.mode,
            "voice_prompt_response_type": context.response_type,
            "voice_prompt_layers_requested": list(layers_requested),
            "voice_prompt_brevity_level": self._effective_brevity_level(
                tone_decision,
                runtime_flags=runtime_flags,
            ),
            "voice_prompt_cta_style": tone_decision.cta_style,
            "voice_prompt_locale": context.locale,
        }
        return VoicePrompt(
            system_prompt="\n".join(system_lines),
            user_prompt="\n".join(user_lines),
            layers_requested=layers_requested,
            brevity_level=self._effective_brevity_level(tone_decision, runtime_flags=runtime_flags),
            cta_style=tone_decision.cta_style,
            observability=observability,
        )

    def _append_list(self, lines: list[str], heading: str, items: list[str]) -> None:
        if not items:
            return
        lines.append(f"{heading}:")
        lines.extend(f"- {item}" for item in items if item)

    async def _resolved_runtime_flags(self) -> VoiceRuntimeFlags:
        if self._voice_runtime_settings_provider is None:
            return self._voice_runtime_flags
        return await self._voice_runtime_settings_provider.get_runtime_flags()

    def _effective_brevity_level(
        self,
        tone_decision: VoiceToneDecision,
        *,
        runtime_flags: VoiceRuntimeFlags,
    ) -> str:
        if runtime_flags.deep_mode_enabled:
            return tone_decision.brevity_level
        return "light" if tone_decision.brevity_level == "light" else "normal"
