from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.reasoning.entities.knowledge_context import KnowledgeContext, StyleKnowledgeCard
from app.domain.reasoning.entities.style_facets import (
    StyleAdviceFacet,
    StyleFacetBundle,
    StyleImageFacet,
    StyleRelationFacet,
    StyleVisualLanguageFacet,
)
from app.domain.style_exploration.entities.diversity_constraints import DiversityConstraints


class PresentationProfile(str, Enum):
    FEMININE = "feminine"
    MASCULINE = "masculine"
    ANDROGYNOUS = "androgynous"
    UNISEX = "unisex"


class ProfileContext(BaseModel):
    presentation_profile: PresentationProfile | None = None
    fit_preferences: list[str] = Field(default_factory=list)
    silhouette_preferences: list[str] = Field(default_factory=list)
    comfort_preferences: list[str] = Field(default_factory=list)
    formality_preferences: list[str] = Field(default_factory=list)
    color_preferences: list[str] = Field(default_factory=list)
    color_avoidances: list[str] = Field(default_factory=list)
    preferred_items: list[str] = Field(default_factory=list)
    avoided_items: list[str] = Field(default_factory=list)

    def snapshot(
        self,
        *,
        source: str = "runtime",
        legacy_values: dict[str, Any] | None = None,
    ) -> "ProfileContextSnapshot":
        return ProfileContextSnapshot(
            presentation_profile=self.presentation_profile.value
            if self.presentation_profile is not None
            else None,
            fit_preferences=tuple(self.fit_preferences),
            silhouette_preferences=tuple(self.silhouette_preferences),
            comfort_preferences=tuple(self.comfort_preferences),
            formality_preferences=tuple(self.formality_preferences),
            color_preferences=tuple(self.color_preferences),
            color_avoidances=tuple(self.color_avoidances),
            preferred_items=tuple(self.preferred_items),
            avoided_items=tuple(self.avoided_items),
            source=source,
            legacy_values=dict(legacy_values or {}),
        )


class ProfileContextSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    presentation_profile: str | None = None
    fit_preferences: tuple[str, ...] = ()
    silhouette_preferences: tuple[str, ...] = ()
    comfort_preferences: tuple[str, ...] = ()
    formality_preferences: tuple[str, ...] = ()
    color_preferences: tuple[str, ...] = ()
    color_avoidances: tuple[str, ...] = ()
    preferred_items: tuple[str, ...] = ()
    avoided_items: tuple[str, ...] = ()
    source: str = "runtime"
    legacy_values: dict[str, Any] = Field(default_factory=dict, exclude=True, repr=False)
    present_override: bool | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_payload(cls, data: Any) -> Any:
        if isinstance(data, ProfileContext):
            return data.snapshot().model_dump()
        if not isinstance(data, dict):
            return data

        raw = dict(data)
        source = _as_optional_str(raw.get("source")) or "runtime"
        values_payload = raw.pop("values", None)
        present_override = raw.pop("present", None)
        legacy_values = dict(raw.pop("legacy_values", {}) or {})

        merged_values: dict[str, Any] = {}
        if isinstance(values_payload, dict):
            merged_values.update(values_payload)
        merged_values.update(raw)

        typed_data = {
            "presentation_profile": _profile_presentation_value(merged_values),
            "fit_preferences": _profile_terms_for_keys(
                merged_values,
                ("fit_preferences", "fit", "fit_preference", "preferred_fit", "body_fit_preference"),
            ),
            "silhouette_preferences": _profile_terms_for_keys(
                merged_values,
                (
                    "silhouette_preferences",
                    "preferred_silhouette",
                    "silhouette",
                    "silhouettes",
                ),
            ),
            "comfort_preferences": _profile_terms_for_keys(
                merged_values,
                (
                    "comfort_preferences",
                    "comfort_preference",
                    "comfort",
                    "mobility_preference",
                ),
            ),
            "formality_preferences": _profile_terms_for_keys(
                merged_values,
                (
                    "formality_preferences",
                    "formality_preference",
                    "formality",
                    "occasion_formality",
                    "dress_code",
                ),
            ),
            "color_preferences": _profile_terms_for_keys(
                merged_values,
                (
                    "color_preferences",
                    "color_preference",
                    "preferred_colors",
                    "preferred_palette",
                    "palette",
                ),
            ),
            "color_avoidances": _profile_terms_for_keys(
                merged_values,
                (
                    "color_avoidances",
                    "avoid_colors",
                    "avoided_colors",
                    "palette_avoidances",
                ),
            ),
            "preferred_items": _profile_terms_for_keys(
                merged_values,
                (
                    "preferred_items",
                    "favorite_items",
                    "preferred_garments",
                    "wardrobe_items",
                ),
            ),
            "avoided_items": _profile_terms_for_keys(
                merged_values,
                (
                    "avoided_items",
                    "avoid_items",
                    "avoided_garments",
                    "avoid_garments",
                    "avoid_hero_garments",
                    "excluded_garments",
                    "unavailable_garments",
                    "forbidden_garments",
                ),
            ),
            "source": source,
            "legacy_values": {
                **legacy_values,
                **_profile_legacy_values(merged_values),
            },
            "present_override": bool(present_override) if isinstance(present_override, bool) else None,
        }
        return typed_data

    @computed_field(return_type=bool)
    @property
    def present(self) -> bool:
        if self.present_override is not None:
            return self.present_override
        return bool(
            self.presentation_profile
            or self.fit_preferences
            or self.silhouette_preferences
            or self.comfort_preferences
            or self.formality_preferences
            or self.color_preferences
            or self.color_avoidances
            or self.preferred_items
            or self.avoided_items
            or self.legacy_values
        )

    @computed_field(return_type=dict[str, Any])
    @property
    def values(self) -> dict[str, Any]:
        values: dict[str, Any] = dict(self.legacy_values)
        if self.presentation_profile:
            values["presentation_profile"] = self.presentation_profile
        tuple_fields = {
            "fit_preferences": self.fit_preferences,
            "silhouette_preferences": self.silhouette_preferences,
            "comfort_preferences": self.comfort_preferences,
            "formality_preferences": self.formality_preferences,
            "color_preferences": self.color_preferences,
            "color_avoidances": self.color_avoidances,
            "preferred_items": self.preferred_items,
            "avoided_items": self.avoided_items,
        }
        for key, items in tuple_fields.items():
            if items:
                values[key] = list(items)
        if self.fit_preferences:
            values.setdefault("fit", self.fit_preferences[0])
            values.setdefault("fit_preference", self.fit_preferences[0])
        if self.silhouette_preferences:
            values.setdefault("silhouette", self.silhouette_preferences[0])
            values.setdefault("preferred_silhouette", self.silhouette_preferences[0])
        if self.comfort_preferences:
            values.setdefault("comfort", self.comfort_preferences[0])
            values.setdefault("comfort_preference", self.comfort_preferences[0])
        if self.formality_preferences:
            values.setdefault("formality", self.formality_preferences[0])
            values.setdefault("dress_code", self.formality_preferences[0])
        if self.color_preferences:
            values.setdefault("color_preference", self.color_preferences[0])
        if self.color_avoidances:
            values.setdefault("avoid_colors", list(self.color_avoidances))
        if self.preferred_items:
            values.setdefault("favorite_items", list(self.preferred_items))
        if self.avoided_items:
            values.setdefault("avoid_items", list(self.avoided_items))
        return values

    def as_profile_context(self) -> ProfileContext:
        return ProfileContext(
            presentation_profile=_presentation_profile_enum(self.presentation_profile),
            fit_preferences=list(self.fit_preferences),
            silhouette_preferences=list(self.silhouette_preferences),
            comfort_preferences=list(self.comfort_preferences),
            formality_preferences=list(self.formality_preferences),
            color_preferences=list(self.color_preferences),
            color_avoidances=list(self.color_avoidances),
            preferred_items=list(self.preferred_items),
            avoided_items=list(self.avoided_items),
        )


class ProfileClarificationDecision(BaseModel):
    should_ask: bool = False
    question_text: str | None = None
    missing_priority_fields: list[str] = Field(default_factory=list)


class UsedStyleReference(BaseModel):
    style_id: int | str | None = None
    style_name: str | None = None
    style_cluster: str | None = None
    silhouette_family: str | None = None
    palette: list[str] = Field(default_factory=list)
    hero_garments: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)


class SessionStateSnapshot(BaseModel):
    user_request: str
    recent_conversation_summary: str | None = None
    active_slots: dict[str, str] = Field(default_factory=dict)
    visual_intent_signal: Literal["advice_only", "open_to_visualization"] | None = None
    visual_intent_required: bool = False
    can_generate_now: bool = False
    locale: str | None = None
    current_style_id: int | str | None = None
    current_style_name: str | None = None
    style_history: list[UsedStyleReference] = Field(default_factory=list)
    diversity_constraints: DiversityConstraints | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReasoningRetrievalQuery(BaseModel):
    mode: str
    user_request: str
    retrieval_profile: str | None = None
    generation_intent: bool = False
    visual_intent_signal: Literal["advice_only", "open_to_visualization"] | None = None
    visual_intent_required: bool = False
    can_generate_now: bool = False
    active_slots: dict[str, str] = Field(default_factory=dict)
    profile_context: ProfileContextSnapshot | None = None
    current_style_id: int | str | None = None
    current_style_name: str | None = None
    locale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_pipeline_inputs(
        cls,
        *,
        mode: str,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
        generation_intent: bool,
    ) -> "ReasoningRetrievalQuery":
        return cls(
            mode=mode,
            user_request=session_state.user_request,
            retrieval_profile=retrieval_profile,
            generation_intent=generation_intent,
            visual_intent_signal=_visual_intent_signal(
                session_state.visual_intent_signal
                or session_state.active_slots.get("visual_intent")
                or session_state.metadata.get("visual_intent_signal")
            ),
            visual_intent_required=bool(
                session_state.visual_intent_required
                or _truthy(session_state.active_slots.get("visual_intent_required"))
                or _truthy(session_state.metadata.get("visual_intent_required"))
            ),
            can_generate_now=session_state.can_generate_now,
            active_slots=dict(session_state.active_slots),
            profile_context=profile_context,
            current_style_id=session_state.current_style_id,
            current_style_name=session_state.current_style_name,
            locale=session_state.locale,
            metadata=dict(session_state.metadata),
        )


class StyleSemanticFragmentSummary(BaseModel):
    style_id: int | str | None = None
    fragment_type: str
    summary: str
    source_ref: str | None = None
    confidence: float = 1.0


class FashionReasoningInput(BaseModel):
    mode: str
    user_request: str
    recent_conversation_summary: str | None = None
    profile_context: ProfileContextSnapshot | None = None
    style_history: list[UsedStyleReference] = Field(default_factory=list)
    diversity_constraints: DiversityConstraints | None = None
    active_slots: dict[str, str] = Field(default_factory=dict)
    knowledge_context: KnowledgeContext = Field(default_factory=KnowledgeContext)
    generation_intent: bool = False
    visual_intent_signal: Literal["advice_only", "open_to_visualization"] | None = None
    visual_intent_required: bool = False
    can_generate_now: bool = False
    retrieval_profile: str | None = None
    style_context: list[StyleKnowledgeCard] = Field(default_factory=list)
    style_advice_facets: list[StyleAdviceFacet] = Field(default_factory=list)
    style_image_facets: list[StyleImageFacet] = Field(default_factory=list)
    style_visual_language_facets: list[StyleVisualLanguageFacet] = Field(default_factory=list)
    style_relation_facets: list[StyleRelationFacet] = Field(default_factory=list)
    style_semantic_fragments: list[StyleSemanticFragmentSummary] = Field(default_factory=list)
    profile_alignment_applied: bool = False
    profile_alignment_notes: list[str] = Field(default_factory=list)
    profile_alignment_filtered_out: list[str] = Field(default_factory=list)
    profile_alignment_boosted_categories: list[str] = Field(default_factory=list)
    profile_alignment_removed_item_types: list[str] = Field(default_factory=list)
    profile_facet_weights: dict[str, float] = Field(default_factory=dict)

    def style_facet_bundle(self) -> StyleFacetBundle:
        return StyleFacetBundle(
            advice_facets=self.style_advice_facets,
            image_facets=self.style_image_facets,
            visual_language_facets=self.style_visual_language_facets,
            relation_facets=self.style_relation_facets,
        )

    def observability_counts(self) -> dict[str, int]:
        style_advice_count = len(self.style_advice_facets)
        style_image_count = len(self.style_image_facets)
        style_visual_count = len(self.style_visual_language_facets)
        style_relation_count = len(self.style_relation_facets)
        return {
            "style_context_count": len(self.style_context),
            "style_facets_count": style_advice_count
            + style_image_count
            + style_visual_count
            + style_relation_count,
            "style_advice_facets_count": style_advice_count,
            "style_image_facets_count": style_image_count,
            "style_visual_language_facets_count": style_visual_count,
            "style_relation_facets_count": style_relation_count,
            "style_semantic_fragments_count": len(self.style_semantic_fragments),
            "style_history_count": len(self.style_history),
            "diversity_constraints_present": int(self.diversity_constraints is not None),
            "visual_intent_signal_present": int(
                self.generation_intent or self.visual_intent_signal is not None
            ),
            "visual_intent_required": int(self.visual_intent_required),
            "profile_alignment_filtered_count": len(self.profile_alignment_filtered_out),
            "profile_alignment_boosted_categories_count": len(self.profile_alignment_boosted_categories),
            "profile_alignment_removed_item_types_count": len(self.profile_alignment_removed_item_types),
            "profile_facet_weights_count": len(self.profile_facet_weights),
            **self.knowledge_context.counts(),
        }


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "required"}


def _visual_intent_signal(
    value: Any,
) -> Literal["advice_only", "open_to_visualization"] | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"advice_only", "text_only", "advice"}:
        return "advice_only"
    if normalized in {"open_to_visualization", "visualize", "visual", "open"}:
        return "open_to_visualization"
    return None


class ImageCtaCandidate(BaseModel):
    cta_text: str
    reason: str
    confidence: float = 1.0
    required_generation_trigger: str | None = None


class ReasoningMetadata(BaseModel):
    routing_mode: str | None = None
    retrieval_profile: str | None = None
    used_providers: list[str] = Field(default_factory=list)
    style_facets_count: int = 0
    style_advice_facets_count: int = 0
    style_image_facets_count: int = 0
    style_visual_language_facets_count: int = 0
    style_relation_facets_count: int = 0
    style_semantic_fragments_count: int = 0
    style_logic_points_count: int = 0
    visual_language_points_count: int = 0
    historical_note_candidates_count: int = 0
    styling_rule_candidates_count: int = 0
    editorial_context_candidates_count: int = 0
    color_poetic_candidates_count: int = 0
    composition_theory_candidates_count: int = 0
    profile_alignment_applied: bool = False
    clarification_required: bool = False
    fashion_brief_built: bool = False
    cta_offered: bool = False
    generation_ready: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_observability(cls, observability: dict[str, Any]) -> "ReasoningMetadata":
        style_advice_count = _as_int(observability.get("style_advice_facets_count"))
        style_image_count = _as_int(observability.get("style_image_facets_count"))
        style_visual_count = _as_int(observability.get("style_visual_language_facets_count"))
        style_relation_count = _as_int(observability.get("style_relation_facets_count"))
        known_keys = {
            "routing_mode",
            "retrieval_profile",
            "used_providers",
            "providers_used",
            "style_advice_facets_count",
            "style_image_facets_count",
            "style_visual_language_facets_count",
            "style_relation_facets_count",
            "style_semantic_fragments_count",
            "style_logic_points_count",
            "visual_language_points_count",
            "historical_note_candidates_count",
            "styling_rule_candidates_count",
            "editorial_context_candidates_count",
            "color_poetic_candidates_count",
            "composition_theory_candidates_count",
            "profile_alignment_applied",
            "clarification_required",
            "fashion_brief_built",
            "cta_offered",
            "generation_ready",
        }
        return cls(
            routing_mode=_as_optional_str(observability.get("routing_mode")),
            retrieval_profile=_as_optional_str(observability.get("retrieval_profile")),
            used_providers=_as_str_list(
                observability.get("used_providers", observability.get("providers_used", []))
            ),
            style_facets_count=style_advice_count
            + style_image_count
            + style_visual_count
            + style_relation_count,
            style_advice_facets_count=style_advice_count,
            style_image_facets_count=style_image_count,
            style_visual_language_facets_count=style_visual_count,
            style_relation_facets_count=style_relation_count,
            style_semantic_fragments_count=_as_int(
                observability.get("style_semantic_fragments_count")
            ),
            style_logic_points_count=_as_int(observability.get("style_logic_points_count")),
            visual_language_points_count=_as_int(
                observability.get("visual_language_points_count")
            ),
            historical_note_candidates_count=_as_int(
                observability.get("historical_note_candidates_count")
            ),
            styling_rule_candidates_count=_as_int(
                observability.get("styling_rule_candidates_count")
            ),
            editorial_context_candidates_count=_as_int(
                observability.get("editorial_context_candidates_count")
            ),
            color_poetic_candidates_count=_as_int(
                observability.get("color_poetic_candidates_count")
            ),
            composition_theory_candidates_count=_as_int(
                observability.get("composition_theory_candidates_count")
            ),
            profile_alignment_applied=bool(observability.get("profile_alignment_applied", False)),
            clarification_required=bool(observability.get("clarification_required", False)),
            fashion_brief_built=bool(observability.get("fashion_brief_built", False)),
            cta_offered=bool(observability.get("cta_offered", False)),
            generation_ready=bool(observability.get("generation_ready", False)),
            extra={key: value for key, value in observability.items() if key not in known_keys},
        )


class FashionReasoningOutput(BaseModel):
    response_type: Literal["text", "clarification", "visual_offer", "generation_ready"]
    text_response: str
    style_logic_points: list[str] = Field(default_factory=list)
    visual_language_points: list[str] = Field(default_factory=list)
    historical_note_candidates: list[str] = Field(default_factory=list)
    styling_rule_candidates: list[str] = Field(default_factory=list)
    editorial_context_candidates: list[str] = Field(default_factory=list)
    color_poetic_candidates: list[str] = Field(default_factory=list)
    composition_theory_candidates: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    can_offer_visualization: bool = False
    suggested_cta: str | None = None
    image_cta_candidates: list[ImageCtaCandidate] = Field(default_factory=list)
    fashion_brief: FashionBrief | None = None
    generation_ready: bool = False
    reasoning_metadata: ReasoningMetadata = Field(default_factory=ReasoningMetadata)
    observability: dict[str, Any] = Field(default_factory=dict)

    def requires_clarification(self) -> bool:
        return self.response_type == "clarification"

    def has_generation_handoff(self) -> bool:
        return self.fashion_brief is not None and self.generation_ready

    def generation_blocked_reason(self) -> str | None:
        if self.has_generation_handoff():
            return None
        if self.requires_clarification():
            return "clarification_required"
        if not self.can_offer_visualization:
            return "visualization_not_offered"
        if self.fashion_brief is None:
            return "fashion_brief_missing"
        if not self.generation_ready:
            return "generation_not_ready"
        return "generation_handoff_unavailable"

    def signal_counts(self) -> dict[str, int]:
        return {
            "style_logic_points_count": len(self.style_logic_points),
            "visual_language_points_count": len(self.visual_language_points),
            "historical_note_candidates_count": len(self.historical_note_candidates),
            "styling_rule_candidates_count": len(self.styling_rule_candidates),
            "editorial_context_candidates_count": len(self.editorial_context_candidates),
            "color_poetic_candidates_count": len(self.color_poetic_candidates),
            "composition_theory_candidates_count": len(self.composition_theory_candidates),
        }


class VoiceContext(BaseModel):
    mode: Literal[
        "general_advice",
        "style_exploration",
        "occasion_outfit",
        "garment_matching",
        "clarification_only",
    ]
    response_type: Literal[
        "text_only",
        "clarification",
        "text_with_brief",
        "text_with_visual_offer",
        "brief_ready_for_generation",
    ]
    desired_depth: Literal["light", "normal", "deep"] = "normal"
    should_be_brief: bool = False
    can_use_historical_layer: bool = False
    can_use_color_poetics: bool = False
    can_offer_visual_cta: bool = False
    profile_context_present: bool = False
    knowledge_density: Literal["low", "medium", "high"] = "medium"
    locale: str = "en"


class StyledAnswer(BaseModel):
    text: str
    tone_profile: str
    voice_layers_used: list[str] = Field(default_factory=list)
    includes_historical_note: bool = False
    includes_color_poetics: bool = False
    cta_text: str | None = None
    brevity_level: str = "normal"
    observability: dict[str, Any] = Field(default_factory=dict)


class VoiceToneDecision(BaseModel):
    base_tone: str
    use_historian_layer: bool = False
    use_color_poetics_layer: bool = False
    brevity_level: str = "normal"
    expressive_density: str = "balanced"
    cta_style: str | None = None


class VoicePrompt(BaseModel):
    system_prompt: str
    user_prompt: str
    layers_requested: list[str] = Field(default_factory=list)
    brevity_level: str = "normal"
    cta_style: str | None = None
    observability: dict[str, Any] = Field(default_factory=dict)


class VoiceCompositionDraft(BaseModel):
    final_text: str
    cta_text: str | None = None
    used_historical_note: bool = False
    used_color_poetics: bool = False
    raw_content: str | None = None
    provider_model: str | None = None


class VoiceLayerReasoningPayload(BaseModel):
    response_type: str
    draft_text: str
    tone_profile: str | None = None
    voice_layers_used: list[str] = Field(default_factory=list)
    includes_historical_note: bool = False
    includes_color_poetics: bool = False
    cta_text: str | None = None
    brevity_level: str = "normal"
    clarification_question: str | None = None
    style_logic_points: list[str] = Field(default_factory=list)
    visual_language_points: list[str] = Field(default_factory=list)
    historical_note_candidates: list[str] = Field(default_factory=list)
    styling_rule_candidates: list[str] = Field(default_factory=list)
    editorial_context_candidates: list[str] = Field(default_factory=list)
    color_poetic_candidates: list[str] = Field(default_factory=list)
    composition_theory_candidates: list[str] = Field(default_factory=list)
    can_offer_visualization: bool = False
    suggested_cta: str | None = None
    observability: dict[str, Any] = Field(default_factory=dict)


class GenerationHandoffPayload(BaseModel):
    generation_ready: bool = False
    fashion_brief: FashionBrief | None = None
    image_cta_candidates: list[ImageCtaCandidate] = Field(default_factory=list)
    blocked_reason: str | None = None
    observability: dict[str, Any] = Field(default_factory=dict)


class FashionReasoningPresentationPayload(BaseModel):
    voice: VoiceLayerReasoningPayload
    generation: GenerationHandoffPayload
    observability: dict[str, Any] = Field(default_factory=dict)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)] if str(value).strip() else []


_PROFILE_CANONICAL_KEYS = {
    "presentation_profile",
    "fit_preferences",
    "silhouette_preferences",
    "comfort_preferences",
    "formality_preferences",
    "color_preferences",
    "color_avoidances",
    "preferred_items",
    "avoided_items",
    "source",
}


def _profile_terms_for_keys(values: dict[str, Any], keys: tuple[str, ...]) -> tuple[str, ...]:
    terms: list[str] = []
    for key in keys:
        terms.extend(_coerce_profile_terms(values.get(key)))
    return tuple(_dedupe_profile_terms(terms))


def _profile_presentation_value(values: dict[str, Any]) -> str | None:
    raw = values.get("presentation_profile")
    normalized = _as_optional_str(raw)
    if normalized is None:
        return None
    lowered = normalized.lower()
    if lowered == "universal":
        return PresentationProfile.UNISEX.value
    if lowered in {member.value for member in PresentationProfile}:
        return lowered
    return lowered


def _presentation_profile_enum(value: str | None) -> PresentationProfile | None:
    normalized = _as_optional_str(value)
    if normalized is None:
        return None
    if normalized.lower() == "universal":
        return PresentationProfile.UNISEX
    try:
        return PresentationProfile(normalized.lower())
    except ValueError:
        return None


def _profile_legacy_values(values: dict[str, Any]) -> dict[str, Any]:
    legacy: dict[str, Any] = {}
    for key, value in values.items():
        if key in _PROFILE_CANONICAL_KEYS or value is None:
            continue
        legacy[key] = value
    return legacy


def _coerce_profile_terms(value: Any) -> list[str]:
    if value is None or isinstance(value, bool):
        return []
    if isinstance(value, str):
        return [part.strip().lower() for part in value.replace(";", ",").split(",") if part.strip()]
    if isinstance(value, tuple | list | set):
        terms: list[str] = []
        for item in value:
            terms.extend(_coerce_profile_terms(item))
        return terms
    text = str(value).strip().lower()
    return [text] if text else []


def _dedupe_profile_terms(terms: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            deduped.append(term)
    return deduped
