from app.application.reasoning.contracts import (
    VoiceCompositionClient,
    VoicePromptBuilder,
    VoiceRuntimeSettingsProvider,
    VoiceTonePolicy,
)
from app.application.reasoning.services.voice_prompt_builder import DefaultVoicePromptBuilder
from app.application.reasoning.services.voice_tone_policy import DefaultVoiceTonePolicy
from app.domain.knowledge.entities import KnowledgeRuntimeFlags
from app.domain.reasoning import (
    FashionReasoningOutput,
    StyledAnswer,
    VoiceCompositionDraft,
    VoiceContext,
    VoiceRuntimeFlags,
)


class DefaultVoiceLayerComposer:
    def __init__(
        self,
        *,
        voice_tone_policy: VoiceTonePolicy | None = None,
        voice_prompt_builder: VoicePromptBuilder | None = None,
        voice_composition_client: VoiceCompositionClient | None = None,
        knowledge_runtime_flags: KnowledgeRuntimeFlags | None = None,
        voice_runtime_flags: VoiceRuntimeFlags | None = None,
        voice_runtime_settings_provider: VoiceRuntimeSettingsProvider | None = None,
        enable_model_composition: bool = False,
    ) -> None:
        self._voice_runtime_flags = voice_runtime_flags or VoiceRuntimeFlags()
        self._voice_runtime_settings_provider = voice_runtime_settings_provider
        self._voice_composition_client = voice_composition_client
        self._enable_model_composition = enable_model_composition
        self._voice_tone_policy = voice_tone_policy or DefaultVoiceTonePolicy(
            voice_runtime_flags=self._voice_runtime_flags,
            voice_runtime_settings_provider=voice_runtime_settings_provider,
        )
        self._voice_prompt_builder = voice_prompt_builder or DefaultVoicePromptBuilder(
            voice_runtime_flags=self._voice_runtime_flags,
            voice_runtime_settings_provider=voice_runtime_settings_provider,
        )
        self._knowledge_runtime_flags = knowledge_runtime_flags or KnowledgeRuntimeFlags()

    async def compose(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
        runtime_flags: KnowledgeRuntimeFlags | None = None,
    ) -> StyledAnswer:
        effective_flags = runtime_flags or self._knowledge_runtime_flags
        effective_voice_flags = await self._resolved_voice_flags()
        filtered_output = self._filtered_reasoning_output(
            reasoning_output=reasoning_output,
            runtime_flags=effective_flags,
            voice_runtime_flags=effective_voice_flags,
        )
        tone_decision = await self._voice_tone_policy.resolve(context)
        voice_prompt = await self._voice_prompt_builder.build(
            filtered_output,
            context,
            tone_decision,
        )
        tone_profile = self._tone_profile(
            voice_layers_used=list(voice_prompt.layers_requested),
            expressive_density=tone_decision.expressive_density,
        )
        llm_error: str | None = None

        if self._enable_model_composition and self._voice_composition_client is not None:
            try:
                draft = await self._voice_composition_client.compose(
                    prompt=voice_prompt,
                    context=context,
                )
                return self._styled_answer_from_model(
                    draft=draft,
                    reasoning_output=filtered_output,
                    voice_prompt=voice_prompt,
                    tone_profile=tone_profile,
                    context=context,
                    voice_runtime_flags=effective_voice_flags,
                )
            except Exception as exc:
                llm_error = str(exc).strip() or exc.__class__.__name__

        voice_layers_used = list(voice_prompt.layers_requested)
        includes_historical_note = False
        includes_color_poetics = False
        text_segments = [self._base_text(reasoning_output=filtered_output).strip()]

        if (
            "historian" in voice_layers_used
            and filtered_output.historical_note_candidates
            and tone_decision.brevity_level != "light"
        ):
            text_segments.append(
                self._historical_sentence(
                    filtered_output.historical_note_candidates[0],
                    locale=context.locale,
                )
            )
            includes_historical_note = True

        color_signal = self._color_signal(filtered_output)
        if (
            "color_poetics" in voice_layers_used
            and color_signal is not None
            and tone_decision.brevity_level != "light"
        ):
            text_segments.append(self._color_sentence(color_signal, locale=context.locale))
            includes_color_poetics = True

        cta_text = self._cta_text(
            reasoning_output=filtered_output,
            cta_style=tone_decision.cta_style,
            voice_runtime_flags=effective_voice_flags,
            locale=context.locale,
        )
        final_text = " ".join(segment for segment in text_segments if segment).strip()
        observability = {
            **dict(voice_prompt.observability),
            "voice_mode": context.mode,
            "voice_response_type": context.response_type,
            "voice_desired_depth": context.desired_depth,
            "voice_knowledge_density": context.knowledge_density,
            "voice_should_be_brief": context.should_be_brief,
            "voice_profile_context_present": context.profile_context_present,
            "voice_can_offer_visual_cta": context.can_offer_visual_cta,
            "voice_layers_used": list(voice_layers_used),
            "voice_tone_profile": tone_profile,
            "voice_historical_used": includes_historical_note,
            "voice_color_poetics_used": includes_color_poetics,
            "voice_brevity_level": voice_prompt.brevity_level,
            "voice_cta_style": voice_prompt.cta_style,
            "voice_cta_present": bool(cta_text),
            "voice_text_length": len(final_text),
            "voice_locale": context.locale,
            "voice_llm_enabled": self._enable_model_composition,
            "voice_llm_attempted": self._enable_model_composition and self._voice_composition_client is not None,
            "voice_llm_used": False,
            "voice_llm_fallback_used": bool(llm_error),
            "voice_llm_error": llm_error,
        }
        return StyledAnswer(
            text=final_text,
            tone_profile=tone_profile,
            voice_layers_used=voice_layers_used,
            includes_historical_note=includes_historical_note,
            includes_color_poetics=includes_color_poetics,
            cta_text=cta_text,
            brevity_level=voice_prompt.brevity_level,
            observability=observability,
        )

    def _styled_answer_from_model(
        self,
        *,
        draft: VoiceCompositionDraft,
        reasoning_output: FashionReasoningOutput,
        voice_prompt,
        tone_profile: str,
        context: VoiceContext,
        voice_runtime_flags: VoiceRuntimeFlags,
    ) -> StyledAnswer:
        voice_layers_used = list(voice_prompt.layers_requested)
        cta_text = self._sanitize_model_cta(
            cta_text=draft.cta_text,
            reasoning_output=reasoning_output,
            cta_style=voice_prompt.cta_style,
            locale=context.locale,
            voice_runtime_flags=voice_runtime_flags,
        )
        includes_historical_note = bool(
            draft.used_historical_note and "historian" in voice_layers_used
        )
        includes_color_poetics = bool(
            draft.used_color_poetics and "color_poetics" in voice_layers_used
        )
        final_text = draft.final_text.strip()
        observability = {
            **dict(voice_prompt.observability),
            "voice_mode": context.mode,
            "voice_response_type": context.response_type,
            "voice_desired_depth": context.desired_depth,
            "voice_knowledge_density": context.knowledge_density,
            "voice_should_be_brief": context.should_be_brief,
            "voice_profile_context_present": context.profile_context_present,
            "voice_can_offer_visual_cta": context.can_offer_visual_cta,
            "voice_layers_used": list(voice_layers_used),
            "voice_tone_profile": tone_profile,
            "voice_historical_used": includes_historical_note,
            "voice_color_poetics_used": includes_color_poetics,
            "voice_brevity_level": voice_prompt.brevity_level,
            "voice_cta_style": voice_prompt.cta_style,
            "voice_cta_present": bool(cta_text),
            "voice_text_length": len(final_text),
            "voice_locale": context.locale,
            "voice_llm_enabled": True,
            "voice_llm_attempted": True,
            "voice_llm_used": True,
            "voice_llm_fallback_used": False,
            "voice_llm_provider_model": draft.provider_model,
            "voice_llm_raw_content_length": len(draft.raw_content or ""),
        }
        return StyledAnswer(
            text=final_text,
            tone_profile=tone_profile,
            voice_layers_used=voice_layers_used,
            includes_historical_note=includes_historical_note,
            includes_color_poetics=includes_color_poetics,
            cta_text=cta_text,
            brevity_level=voice_prompt.brevity_level,
            observability=observability,
        )

    def _filtered_reasoning_output(
        self,
        *,
        reasoning_output: FashionReasoningOutput,
        runtime_flags: KnowledgeRuntimeFlags,
        voice_runtime_flags: VoiceRuntimeFlags,
    ) -> FashionReasoningOutput:
        return reasoning_output.model_copy(
            update={
                "historical_note_candidates": (
                    list(reasoning_output.historical_note_candidates)
                    if runtime_flags.use_historical_context and voice_runtime_flags.historian_enabled
                    else []
                ),
                "editorial_context_candidates": (
                    list(reasoning_output.editorial_context_candidates)
                    if runtime_flags.use_editorial_knowledge
                    else []
                ),
                "color_poetic_candidates": (
                    list(reasoning_output.color_poetic_candidates)
                    if runtime_flags.use_color_poetics and voice_runtime_flags.color_poetics_enabled
                    else []
                ),
                "composition_theory_candidates": (
                    list(reasoning_output.composition_theory_candidates)
                    if runtime_flags.use_color_poetics and voice_runtime_flags.color_poetics_enabled
                    else []
                ),
            }
        )

    def _historical_sentence(self, note: str, *, locale: str) -> str:
        normalized = note.strip().rstrip(".")
        if self._is_russian_locale(locale):
            return (
                "\u0418\u0441\u0442\u043e\u0440\u0438\u0447\u0435\u0441\u043a\u0438 "
                f"\u044d\u0442\u043e \u043e\u0442\u0441\u044b\u043b\u0430\u0435\u0442 "
                f"\u043a {self._lowercase_first(normalized)}."
            )
        return f"Historically, {normalized}."

    def _color_signal(self, reasoning_output: FashionReasoningOutput) -> str | None:
        for candidate in (
            *reasoning_output.color_poetic_candidates,
            *reasoning_output.composition_theory_candidates,
            *reasoning_output.visual_language_points,
        ):
            normalized = candidate.strip()
            if normalized:
                return normalized
        return None

    def _color_sentence(self, signal: str, *, locale: str) -> str:
        normalized = signal.strip().rstrip(".")
        if self._is_russian_locale(locale):
            return (
                "\u0412\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e "
                f"\u0437\u0434\u0435\u0441\u044c \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 "
                f"{self._lowercase_first(normalized)}."
            )
        return f"Visually, {normalized}."

    def _cta_text(
        self,
        *,
        reasoning_output: FashionReasoningOutput,
        cta_style: str | None,
        voice_runtime_flags: VoiceRuntimeFlags,
        locale: str,
    ) -> str | None:
        if (
            not cta_style
            or not reasoning_output.can_offer_visualization
            or not reasoning_output.suggested_cta
        ):
            return None
        seed = reasoning_output.suggested_cta.strip()
        if not seed:
            return None
        seed_core = seed.rstrip(".!?")
        if cta_style == "neutral":
            return seed
        if cta_style == "soft":
            if self._is_russian_locale(locale):
                return f"\u0415\u0441\u043b\u0438 \u0445\u043e\u0447\u0435\u0448\u044c, {self._lowercase_first(seed_core)}."
            return f"If you want, {self._lowercase_first(seed_core)}."
        if cta_style == "editorial_soft":
            if self._is_russian_locale(locale):
                return (
                    "\u0415\u0441\u043b\u0438 \u0431\u0443\u0434\u0435\u0442 "
                    "\u043f\u043e\u043b\u0435\u0437\u043d\u043e, "
                    f"{self._lowercase_first(seed_core)}, "
                    "\u0447\u0442\u043e\u0431\u044b \u0443\u0432\u0438\u0434\u0435\u0442\u044c "
                    "\u043b\u043e\u0433\u0438\u043a\u0443 \u043e\u0431\u0440\u0430\u0437\u0430 "
                    "\u0432\u0438\u0437\u0443\u0430\u043b\u044c\u043d\u043e."
                )
            return (
                "If it helps, "
                f"{self._lowercase_first(seed_core)} so you can see the logic visually."
            )
        if cta_style == "editorial_soft_experimental" and voice_runtime_flags.cta_experimental_copy_enabled:
            if self._is_russian_locale(locale):
                return (
                    "\u0415\u0441\u043b\u0438 \u0431\u0443\u0434\u0435\u0442 "
                    "\u043f\u043e\u043b\u0435\u0437\u043d\u043e, "
                    f"{self._lowercase_first(seed_core)}, "
                    "\u0447\u0442\u043e\u0431\u044b \u0441\u0438\u043b\u0443\u044d\u0442, "
                    "\u043f\u0430\u043b\u0438\u0442\u0440\u0430 \u0438 \u0440\u0438\u0442\u043c "
                    "\u0441\u0440\u0430\u0437\u0443 \u0447\u0438\u0442\u0430\u043b\u0438\u0441\u044c "
                    "\u0432 \u043e\u0434\u043d\u043e\u043c \u043a\u0430\u0434\u0440\u0435."
                )
            return (
                "If it helps, "
                f"{self._lowercase_first(seed_core)} so the silhouette, palette, and spacing can be read in one frame."
            )
        return seed

    def _tone_profile(self, *, voice_layers_used: list[str], expressive_density: str) -> str:
        if voice_layers_used == ["stylist"]:
            return f"smart_stylist_{expressive_density}"
        return f"smart_stylist_with_{'_and_'.join(voice_layers_used[1:])}_{expressive_density}"

    def _lowercase_first(self, text: str) -> str:
        if not text:
            return text
        if text.startswith("I ") or text.startswith("I'"):
            return text
        return text[:1].lower() + text[1:]

    def _base_text(self, *, reasoning_output: FashionReasoningOutput) -> str:
        if reasoning_output.response_type == "clarification" and reasoning_output.clarification_question:
            return reasoning_output.clarification_question
        return reasoning_output.text_response

    def _sanitize_model_cta(
        self,
        *,
        cta_text: str | None,
        reasoning_output: FashionReasoningOutput,
        cta_style: str | None,
        locale: str,
        voice_runtime_flags: VoiceRuntimeFlags,
    ) -> str | None:
        normalized = cta_text.strip() if isinstance(cta_text, str) else ""
        if normalized:
            return normalized
        return self._cta_text(
            reasoning_output=reasoning_output,
            cta_style=cta_style,
            voice_runtime_flags=voice_runtime_flags,
            locale=locale,
        )

    def _is_russian_locale(self, locale: str | None) -> bool:
        normalized = (locale or "").strip().lower()
        return normalized.startswith("ru")

    async def _resolved_voice_flags(self) -> VoiceRuntimeFlags:
        if self._voice_runtime_settings_provider is None:
            return self._voice_runtime_flags
        return await self._voice_runtime_settings_provider.get_runtime_flags()
