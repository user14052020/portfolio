from typing import Any, Literal

from pydantic import BaseModel, Field

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


class ProfileContextSnapshot(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    present: bool = False
    source: str = "runtime"


class UsedStyleReference(BaseModel):
    style_id: int | str | None = None
    style_name: str | None = None
    style_cluster: str | None = None
    palette: list[str] = Field(default_factory=list)
    hero_garments: list[str] = Field(default_factory=list)
    visual_motifs: list[str] = Field(default_factory=list)


class SessionStateSnapshot(BaseModel):
    user_request: str
    recent_conversation_summary: str | None = None
    active_slots: dict[str, str] = Field(default_factory=dict)
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
    profile_facet_weights: dict[str, float] = Field(default_factory=dict)

    def style_facet_bundle(self) -> StyleFacetBundle:
        return StyleFacetBundle(
            advice_facets=self.style_advice_facets,
            image_facets=self.style_image_facets,
            visual_language_facets=self.style_visual_language_facets,
            relation_facets=self.style_relation_facets,
        )

    def observability_counts(self) -> dict[str, int]:
        return {
            "style_context_count": len(self.style_context),
            "style_advice_facets_count": len(self.style_advice_facets),
            "style_image_facets_count": len(self.style_image_facets),
            "style_visual_language_facets_count": len(self.style_visual_language_facets),
            "style_relation_facets_count": len(self.style_relation_facets),
            "style_semantic_fragments_count": len(self.style_semantic_fragments),
            "style_history_count": len(self.style_history),
            "diversity_constraints_present": int(self.diversity_constraints is not None),
            "profile_alignment_filtered_count": len(self.profile_alignment_filtered_out),
            "profile_facet_weights_count": len(self.profile_facet_weights),
            **self.knowledge_context.counts(),
        }


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


class VoiceLayerReasoningPayload(BaseModel):
    response_type: str
    draft_text: str
    clarification_question: str | None = None
    style_logic_points: list[str] = Field(default_factory=list)
    visual_language_points: list[str] = Field(default_factory=list)
    historical_note_candidates: list[str] = Field(default_factory=list)
    styling_rule_candidates: list[str] = Field(default_factory=list)
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
