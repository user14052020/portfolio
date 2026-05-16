# Reasoning Pipeline Plan Audit

Audit date: 2026-04-27

Source plan:
`docs/upd-2/3-reasoning_pipeline.md`

Scope:
- section 22 implementation substeps
- section 23 acceptance criteria
- section 24 definition of done
- critical contract expectations from sections 5-21

Note:
- Builds were intentionally not run.
- Reasoning pipeline tests were run.
- This audit maps implemented files, contract behavior, and regression coverage to the plan.

Executed verification:
- `python -B -m unittest apps/backend/tests/test_reasoning_pipeline_contracts.py apps/backend/tests/test_reasoning_pipeline_orchestration_adapter.py apps/backend/tests/test_stylist_orchestrator.py`
- Result: `Ran 68 tests`, `OK`

---

## Section 22 Implementation Substeps

1. Update contracts: covered.
   Evidence: `apps/backend/app/domain/reasoning/entities/reasoning_contracts.py`,
   `apps/backend/app/domain/reasoning/entities/knowledge_context.py`,
   `apps/backend/app/domain/prompt_building/entities/fashion_brief.py`,
   `apps/backend/app/domain/reasoning/entities/style_facets.py`.

2. Implement retrieval assembler: covered.
   Evidence: `apps/backend/app/application/reasoning/services/fashion_reasoning_context_assembler.py`,
   retrieval profile selector, style history loading, diversity constraints loading,
   semantic fragments loading, and `KnowledgeContext.style_history_cards`.

3. Implement profile alignment: covered.
   Evidence: `apps/backend/app/application/reasoning/services/profile_style_alignment_service.py`,
   `apps/backend/app/application/reasoning/services/profile_aligned_reasoning_context_assembler.py`,
   and alignment tests in `test_reasoning_pipeline_contracts.py`.

4. Update reasoner: covered.
   Evidence: `apps/backend/app/application/reasoning/services/fashion_reasoner.py`.
   Covered behaviors include richer facet reasoning, clarification-first policy,
   CTA preparation, anti-repeat reroute, semantic fragment downstream use,
   knowledge/editorial historical references, and structured reasoning signals.

5. Extract `FashionBriefBuilder`: covered.
   Evidence: `apps/backend/app/application/reasoning/services/fashion_brief_builder.py`
   with dedicated unit coverage in `test_reasoning_pipeline_contracts.py`.

6. Connect to orchestration: covered.
   Evidence: `apps/backend/app/application/reasoning/services/fashion_reasoning_pipeline.py`,
   `apps/backend/app/application/stylist_chat/orchestrator/stylist_chat_orchestrator.py`,
   reasoning output mapper, and orchestration adapter/orchestrator tests.

7. Add observability and regression tests: covered.
   Evidence: reasoning observability fields in reasoner/pipeline/orchestrator,
   compare-output regressions, anti-repeat checks, semantic-fragment regressions,
   and voice/generation handoff telemetry tests.

---

## Critical Contract Coverage From Sections 5-21

### FashionReasoningInput and richer facet bundles

- Covered.
  Evidence: `FashionReasoningInput` includes `style_context`,
  `style_advice_facets`, `style_image_facets`,
  `style_visual_language_facets`, `style_relation_facets`,
  `style_semantic_fragments`, `style_history`, and `diversity_constraints`.

### KnowledgeContext richer structure

- Covered.
  Evidence: `KnowledgeContext` now carries `knowledge_cards`, `style_cards`,
  `style_advice_cards`, `style_visual_cards`, `style_history_cards`,
  and `editorial_cards`.
  Typed `style_advice_cards` and `style_visual_cards` now also participate
  in downstream reasoning synthesis instead of remaining contract-only fields.
  Typed `style_history_cards` now also participate in anti-repeat reasoning
  as fallback sources for recent style labels and repeated visual motifs,
  both in `FashionReasoner` and in `FashionBriefBuilder` consistency paths.

### FashionReasoner as retrieval-to-generation bridge

- Covered.
  Evidence: reasoner interprets user need, aligns it with structured style knowledge,
  applies clarification policy, returns structured signals for voice,
  and prepares generation decision state without calling generation directly.

### FashionBrief richer normalized brief

- Covered.
  Evidence: `FashionBriefBuilder` populates `garment_list`, `palette`,
  `materials`, `footwear`, `accessories`, `props`, `visual_motifs`,
  `lighting_mood`, `photo_treatment`, `composition_rules`,
  `negative_constraints`, `historical_reference`, `knowledge_cards`,
  `occasion_context`, `anchor_garment`, `visual_preset`,
  and diversity metadata from structured sources.
  `negative_constraints` now explicitly include advice/image signals,
  anti-repeat constraints, and profile-alignment filtered elements.
  Richer facet fields such as `overlap_context`, `mood_keywords`,
  `platform_visual_cues`, `brands`, and `platforms` now also flow
  downstream into reasoning output and brief metadata/reference fields.

### Profile alignment inside reasoning

- Covered.
  Evidence: `DefaultProfileStyleAlignmentService` filters and reprioritizes
  advice/image/visual/relation facets before reasoning, and the aligned assembler
  pushes these results downstream.
  `profile_facet_weights` are now also consumed by the reasoner and
  `FashionBriefBuilder` for downstream facet ordering.

### Diversity and anti-repeat

- Covered.
  Evidence: recent palettes, hero garments, and visual motifs are loaded into
  reasoning input; reasoner chooses adjacent directions when requested,
  filters repeated visual motifs and avoided palettes from user-facing visual cues,
  downweights repeated image cues for CTA/image-strength decisions,
  and brief generation carries anti-repeat negative constraints.

### Clarification-first policy

- Covered.
  Evidence: reasoner returns clarification for missing `occasion`, `weather`,
  `silhouette preference`, and generation permission conflicts.
  Clarification path returns `fashion_brief=None` and blocks generation handoff.

### CTA logic after reasoning

- Covered.
  Evidence: reasoner returns `can_offer_visualization`, `suggested_cta`,
  `image_cta_candidates`, explicit `cta_decision_reason`, and
  `cta_blocked_reasons`; CTA depends on image-context strength,
  visual-language quality, generation intent, explicit visual-intent signal,
  profile-signal sufficiency, and advisory bias.

### Knowledge-layer integration

- Covered.
  Evidence: provider-oriented retrieval contracts, `StyleDistilledReasoningProvider`,
  semantic fragments, history cards, knowledge cards, and editorial cards
  all feed the reasoning layer without parser-SQL coupling.

### Voice-layer integration

- Covered.
  Evidence: reasoning output exposes `text_response`, `style_logic_points`,
  `visual_language_points`, `historical_note_candidates`,
  and `styling_rule_candidates`, which are mapped by
  `DefaultReasoningOutputMapper` into a dedicated voice payload, with
  dedicated mapper regression coverage asserting those fields survive
  voice/generation presentation splitting unchanged.

### Observability and tests

- Covered.
  Evidence: metadata/observability contain routing mode, retrieval profile,
  provider usage, aggregated `style_facets_count`, profile alignment state, clarification state,
  brief build state, explicit CTA decision/blocker reasons, generation readiness,
  explicit `generation_blocked_reason`, output signal counts for style/visual/history/rules,
  anti-repeat details, CTA confidence / advisory / profile-sufficiency signals,
  and orchestrator-level voice/generation telemetry with mirrored event + metric coverage.

### Degree of visual intent

- Covered through explicit contract-level visual-intent signaling, runtime branching,
  and CTA-confidence behavior.
  Evidence: `SessionStateSnapshot`, `ReasoningRetrievalQuery`, and
  `FashionReasoningInput` now carry `visual_intent_signal` and
  `visual_intent_required`; reasoner can return clarification when
  `visual_intent_required=true` but no signal is provided, observability exposes
  `visual_intent_signal_present`, and compare regression coverage still proves
  that the same structured reasoning context stays `visual_offer` when
  `generation_intent=false` and becomes `generation_ready` when
  `generation_intent=true`; explicit `advice_only` versus
  `open_to_visualization` signals also adjust advisory bias and
  `cta_confidence_score` without forcing premature generation handoff.

---

## Section 23 Acceptance Criteria

1. Reasoning pipeline uses semantic-distilled parser output: covered.
   Evidence: semantic fragments and distilled provider projections are consumed
   downstream by reasoner and brief builder.

2. `FashionReasoningInput` supports richer style facets: covered.
   Evidence: richer facet and history/diversity contracts are implemented.

3. Retrieval is extracted into `FashionReasoningContextAssembler`: covered.
   Evidence: dedicated assembler and retrieval-profile selection.

4. `ProfileStyleAlignmentService` exists: covered.
   Evidence: dedicated service and aligned assembler wrapper.

5. `FashionBrief` is built from advice/image/visual-language facets: covered.
   Evidence: builder aggregates all three facet groups plus aligned filters.

6. Reasoner returns structured reasoning signals, not only text: covered.
   Evidence: `style_logic_points`, `visual_language_points`,
   `historical_note_candidates`, `styling_rule_candidates`,
   CTA fields, and observability metadata.

7. Visualization CTA depends on style/image context quality: covered.
   Evidence: reasoner CTA logic uses image-context strength and visual-language presence.

8. Reasoning is not directly coupled to parser SQL schema: covered.
   Evidence: reasoning domain/application layers are SQL-free and use contracts only.

9. Voice layer can formulate enriched output without rebuilding fashion logic: covered.
   Evidence: dedicated mapper and payload structure, plus voice/generation split tests.

10. Generation handoff receives richer normalized brief: covered.
    Evidence: generation-ready pipeline path returns populated `FashionBrief`.

---

## Section 24 Definition Of Done

- Reasoning no longer relies only on coarse `style_profiles`: covered.
- Parser upgrade is used downstream for actual reasoning behavior: covered.
- Richer style provider can be connected without reworking the reasoning architecture: covered.
- `FashionBrief` and user-facing response stay consistent: covered.
  Evidence: mapper consistency tests and anti-repeat consistency regression tests.
- Architecture remains clean, extensible, and maintainable: covered.
  Evidence: protocol-based contracts, dedicated services by responsibility,
  orchestration separation, and SQL-free reasoning layers.

---

## Residual Note

- This audit is based on current implementation plus targeted reasoning tests.
- Builds were intentionally skipped as requested.
- Visual-intent coverage is now explicit at the contract level via
  `visual_intent_signal` and `visual_intent_required`; any older indirect-only
  interpretation should be treated as superseded.
- The "degree of visual intent" requirement is now represented both through
  explicit `visual_intent_signal` / `visual_intent_required` contracts and
  through downstream CTA-confidence behavior, not only through routed
  `generation_intent`.
