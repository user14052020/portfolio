# Profile Context Plan Audit

Audit date: 2026-04-27

Source plan:
`docs/upd-2/4-profile_context_full.md`

Scope:
- section 23 observability
- section 24 testing
- section 25 architecture / SOLID
- section 26 implementation substeps
- section 27 acceptance criteria
- section 28 definition of done
- critical behavior from sections 8-18

Note:
- Builds were intentionally not run.
- Backend profile-context regressions were run.
- Frontend product tests were added, but not executed locally because
  `apps/frontend/node_modules` and a local `tsx` runner are absent.

Executed verification:
- `python -B -m unittest tests/test_build_knowledge_query.py tests/test_profile_session_state.py tests/test_profile_context_layer.py tests/test_reasoning_pipeline_contracts.py tests/test_reasoning_pipeline_orchestration_adapter.py tests/test_stylist_orchestrator.py tests/test_generation_request_builder.py tests/test_routing_context_builder.py tests/test_fashion_brief_builder.py tests/test_enriched_runtime_consumption_integration.py tests/test_stylist_service_profile_context.py tests/test_stylist_service_context.py tests/test_knowledge_ranker.py tests/test_style_catalog_repository.py tests/test_knowledge_retrieval_service.py tests/test_image_prompt_compiler_stage7.py tests/test_reasoning_context_builder.py tests/test_garment_matching_handler.py tests/test_occasion_outfit_handler.py tests/test_knowledge_layer_e2e.py`
- Result: `Ran 149 tests`, `OK (skipped=4)`

---

## Section 26 Implementation Substeps

1. Update domain contracts: covered.
   Evidence: `apps/backend/app/domain/reasoning/entities/reasoning_contracts.py`,
   `apps/backend/app/domain/reasoning/entities/style_facets.py`.
   Covered contracts include `ProfileContext`, `ProfileContextSnapshot`,
   `ProfileClarificationDecision`, and the expanded
   `ProfileAlignedStyleFacetBundle`.

2. Implement `ProfileContextNormalizer`: covered.
   Evidence: `apps/backend/app/application/reasoning/services/profile_context_normalizer.py`.
   Covered behavior includes normalization, deduplication, closed-set coercion,
   list limits, and legacy compatibility for keys like `gender`, `fit`,
   `silhouette`, `comfort`, `dress_code`, and `avoid_items`.

3. Implement `ProfileContextService`: covered.
   Evidence: `apps/backend/app/application/reasoning/services/profile_context_service.py`.
   Covered behavior includes merge order
   `persistent -> session -> frontend -> recent updates` and snapshot output
   for the reasoning pipeline.

4. Implement `ProfileClarificationPolicy`: covered.
   Evidence: `apps/backend/app/application/reasoning/services/profile_clarification_policy.py`.
   Covered behavior includes deciding when to ask, which profile field is
   higher priority, and when it is safe to skip clarification.
   Current contextual questions now cover:
   - silhouette preference for `occasion_outfit`
   - presentation direction for partial `style_exploration` profiles
   - wearability / expressiveness preference when style exploration bundles
     contain both casual adaptations and stronger statement paths

5. Implement `ProfileStyleAlignmentService`: covered.
   Evidence: `apps/backend/app/application/reasoning/services/profile_style_alignment_service.py`.
   Covered behavior includes hard excludes, soft boosts, soft penalties,
   wearable adaptation, filtered outputs, boosted facet categories,
   removed item types, and downstream facet weights.

6. Thread profile context through runtime: covered.
   Evidence:
   - `apps/backend/app/application/stylist_chat/services/routing_context_builder.py`
   - `apps/backend/app/application/stylist_chat/services/reasoning_pipeline_decision_adapter.py`
   - `apps/backend/app/application/knowledge/use_cases/build_knowledge_query.py`
   - `apps/backend/app/application/reasoning/services/profile_aligned_reasoning_context_assembler.py`
   - `apps/backend/app/application/reasoning/services/fashion_brief_builder.py`
   - `apps/backend/app/application/stylist_chat/services/generation_request_builder.py`
   - `apps/backend/app/application/prompt_building/services/prompt_pipeline_builder.py`
   - `apps/backend/app/application/prompt_building/services/generation_payload_builder.py`
   - `apps/backend/app/application/visual_generation/services/generation_payload_assembler.py`

   Backend session persistence for profile context is also covered:
   - `apps/backend/app/domain/chat_context.py`
   - `apps/backend/app/services/profile_session_state.py`
   - `apps/backend/app/services/stylist_conversational.py`

   This closes the literal Stage 4 requirement that profile context should live
   in runtime before reasoning and stay available in backend session state.
   `ChatCommand.profile_context` itself is now built from the resolved
   session-normalized profile state plus derived body hints, so legacy context
   builders no longer silently fall back to raw frontend payload only.
   The legacy knowledge-retrieval branch no longer bypasses profile
   normalization: `BuildKnowledgeQueryUseCase` now resolves a merged normalized
   profile snapshot before retrieval instead of sending raw
   `command.profile_context` downstream.

7. Update frontend: covered.
   Evidence:
   - `apps/frontend/src/entities/profile/model/types.ts`
   - `apps/frontend/src/entities/profile/model/profileContext.ts`
   - `apps/frontend/src/processes/stylist-chat/model/lib.ts`
   - `apps/frontend/src/processes/stylist-chat/model/useStylistChatProcess.ts`
   - `apps/frontend/src/widgets/stylist-chat-panel/ui/ChatClarificationPanel.tsx`
   - `apps/frontend/src/shared/api/gateways/chatGateway.ts`
   - `apps/frontend/src/shared/api/gateways/commandGateway.ts`
   - `apps/frontend/src/shared/api/gateways/visualizationGateway.ts`
   - `apps/frontend/src/features/send-chat-message/model/sendChatMessage.ts`
   - `apps/frontend/src/features/followup-clarification/model/submitFollowupClarification.ts`
   - `apps/frontend/src/features/run-chat-command/model/runChatCommand.ts`
   - `apps/frontend/src/features/chat-request-visualization/model/requestVisualization.ts`

   Covered behavior includes `localStorage`, request payloads,
   clarification UI quick picks, and profile patch updates from follow-up answers.

8. Add observability and tests: covered.
   Evidence:
   - `apps/backend/app/application/reasoning/services/fashion_reasoner.py`
   - `apps/backend/app/application/stylist_chat/services/reasoning_pipeline_decision_adapter.py`
   - `apps/backend/app/application/stylist_chat/orchestrator/stylist_chat_orchestrator.py`
   - backend tests listed below
   - frontend product/contract tests added under `apps/frontend/tests`

---

## Critical Coverage From Sections 8-18

### Profile layer architecture

- Covered.
  `ProfileContextService`, `ProfileContextNormalizer`,
  `ProfileClarificationPolicy`, and `ProfileStyleAlignmentService`
  exist as separate services instead of being smeared across handlers.

### Profile enters runtime before reasoning

- Covered.
  Routing sees profile hints before reasoning.
  The aligned reasoning context assembler runs before `FashionReasoner`.
  `FashionBrief`, generation handoff, prompt compilation, and visual generation
  consume profile-aware outputs instead of trying to patch personalization late.

### Prompt compilation and generation constraints

- Covered.
  Profile-derived constraints are now actively used during prompt compilation,
  not only stored in payload metadata.
  Evidence:
  - `apps/backend/app/application/prompt_building/services/image_prompt_compiler.py`

  Current prompt compilation uses:
  - positive profile framing in the final prompt
  - profile avoidances in the negative prompt
  - downstream propagation into `VisualGenerationPlan` and `GenerationMetadata`

### Retrieval shaping before alignment

- Covered.
  Profile context now influences retrieval as a soft weighting signal in both:
  - `apps/backend/app/infrastructure/knowledge/repositories/style_catalog_repository.py`
  - `apps/backend/app/application/knowledge/services/knowledge_ranker.py`
  - `apps/backend/app/application/knowledge/use_cases/build_knowledge_query.py`
  - `apps/backend/app/application/stylist_chat/services/reasoning_context_builder.py`

  This closes the literal Stage 4 requirement from section 15 that profile may
  affect retrieval priorities before alignment, while still avoiding a hard
  retriever gate.
  The non-reasoning knowledge-query path now also uses `ProfileContextService`
  before retrieval, so `KnowledgeQuery.profile_context` is a merged normalized
  snapshot rather than a raw frontend payload.
  The legacy `knowledge_provider.fetch(query=...)` path now also carries
  runtime `profile_context` and derived body proportions in the query payload,
  instead of dropping profile hints entirely before retrieval.

### Backend session storage

- Covered.
  `ChatModeContext` now carries:
  - `session_profile_context`
  - `profile_context_snapshot`
  - `profile_recent_updates`
  - `profile_completeness_state`

  `StylistService` now resolves, persists, and reuses that state through
  `ProfileSessionStateService`, which keeps backend session consistency even if
  frontend hints are incomplete on a later request.
  `profile_completeness_state` is now derived in the profile layer during
  session-state resolution, so backend session storage no longer depends on
  reasoning telemetry as its first source of truth for completeness.
  This now also preserves passthrough extension fields like `height_cm` /
  `weight_kg`, instead of silently dropping them during snapshot compaction.

### Frontend storage and UX

- Covered.
  `localStorage` holds profile context, chat UI state keeps it across refresh,
  and clarification answers can patch profile state progressively.
  Frontend clarification extraction / quick picks already support:
  - presentation questions
  - silhouette questions
  - wearability / expressiveness questions
  - wording consistency between `universal` clarification copy and canonical
    stored `unisex` runtime value
  - passthrough extension profile fields survive frontend normalization,
    localStorage persistence, and request-envelope building instead of being
    dropped by the typed core

### Future-ready persistent profile

- Covered as architecture-ready, not as a fully implemented persistent profile store.
  Evidence:
  - `ProfileContextInput` already models `persistent_profile`
  - `ProfileContextService` already merges it first in priority order
  - runtime metadata and session helpers preserve a place for future
    `persistent_profile_context`

  This matches the plan language that persistent profile support must be
  future-ready rather than necessarily fully implemented now.
  The runtime now preserves unknown extension fields through
  `ProfileContextInput -> ProfileContextSnapshot -> backend session state`,
  so later profile expansion is not blocked by the current typed core.

### Anti-repeat inside preference envelope

- Covered.
  Profile alignment and reasoning together influence garment selection,
  silhouette logic, negative constraints, CTA quality, brief quality,
  and anti-repeat diversification.
  This now includes the literal Stage 4 `recently recommended silhouettes`
  requirement through `UsedStyleReference.silhouette_family`,
  `DiversityConstraints.avoid_silhouette_families`, and
  `KnowledgeContext.style_history_cards` metadata / summaries.

---

## Section 23 Observability

### Required profile observability fields

- Covered.
  Current telemetry includes:
  - `profile_completeness_state`
  - `profile_clarification_decision`
  - `profile_clarification_required`
  - `profile_alignment_applied`
  - `profile_alignment_filtered_count`
  - `profile_alignment_boosted_categories`
  - `profile_alignment_removed_item_types`
  - `profile_context_present`
  - `profile_context_source`
  - `profile_fields_count`
  - `profile_derived_constraints_count`

### Where it is logged

- Covered.
  Reasoner writes the raw profile observability.
  Adapter normalizes it into orchestration telemetry.
  Orchestrator writes it into:
  - `stylist_chat_orchestrated` event payload
  - metrics counters / observations

### Why this matters

- Covered.
  The system can now explain:
  - why profile clarification was asked or skipped
  - why alignment filtered or boosted certain cues
  - how much profile signal was actually available
  - how many profile-derived constraints survived into `FashionBrief`

---

## Section 24 Testing

### 24.1 Unit tests

- Covered.
  Evidence:
  - `tests/test_build_knowledge_query.py`
  - `tests/test_profile_context_layer.py`
  - `tests/test_profile_session_state.py`
  - `tests/test_stylist_service_profile_context.py`
  - `tests/test_reasoning_pipeline_contracts.py`

  This covers:
  - `ProfileContextNormalizer`
  - `ProfileContextService`
  - `ProfileClarificationPolicy`
  - `ProfileStyleAlignmentService`
  - session profile merge / reset persistence helpers

### 24.2 Integration tests

- Covered.
  Evidence:
  - `tests/test_reasoning_pipeline_contracts.py`
  - `tests/test_reasoning_pipeline_orchestration_adapter.py`
  - `tests/test_generation_request_builder.py`
  - `tests/test_enriched_runtime_consumption_integration.py`

  Covered scenarios include:
- no profile -> safe response
- partial profile -> clarification / partial completeness
- stronger profile -> aligned reasoning
- non-reasoning retrieval query receives merged normalized profile context
- profile affects `FashionBrief`
- profile affects generation constraints
- `universal` presentation replies normalize to canonical `unisex` across
  frontend extraction, backend normalization, and snapshot coercion
- passthrough profile extensions like `height_cm` / `weight_kg` survive
  profile service snapshotting and backend session reuse
- profile interacts with anti-repeat and silhouette constraints
- repeated silhouettes are carried from session history into diversity
  constraints and history-card fallbacks

### 24.3 Product tests

- Covered at file level.
  Evidence:
  - `apps/frontend/tests/stylist-chat.contract.test.ts`
  - `apps/frontend/tests/stylist-runtime-product.contract.test.ts`

  These cover:
  - profile request envelope
  - clarification update extraction
  - extension field continuity through frontend normalization / envelope logic
  - frontend profile continuity / persistence

  Status note:
  - present in repo
  - not executed locally in this audit pass because frontend test runtime is not installed

---

## Section 25 Clean Architecture / SOLID

### 25.1 Domain layer

- Covered.
  `ProfileContext`, `ProfileContextSnapshot`,
  `ProfileAlignedStyleFacetBundle`, and `ProfileClarificationDecision`
  are isolated in the domain layer.

### 25.2 Application layer

- Covered.
  Profile normalization, merge, clarification, and alignment live in separate
  application services.

### 25.3 Infrastructure layer

- Covered for the current plan scope.
  - backend session profile persistence:
    `ChatModeContext`, `ChatContextStore`, `ProfileSessionStateService`
  - localStorage payload adapters:
    frontend `profileContext.ts`, persisted chat UI state
  - telemetry/logging:
    reasoner -> adapter -> orchestrator metrics/event path

### 25.4 Interface layer

- Covered for the current plan scope.
  - clarification UI: implemented
  - API DTOs: implemented
  - session middleware hooks: effectively covered by backend session context
    persistence inside `StylistService` and `ChatContextStore`
  - frontend profile UI: implemented as conversational profile UI rather than
    a separate dedicated settings surface

### 25.5 SOLID emphasis

- Covered.
  SRP:
  storage, normalization, clarification, alignment, and session merge are separated.

  OCP:
  new profile fields extend typed contracts and normalizer/service logic without
  forcing a rewrite of the reasoning core.

  DIP:
  reasoner depends on snapshot/aligned bundles rather than DB schema or raw frontend payload.

---

## Section 27 Acceptance Criteria

1. Profile context is no longer only a generation-step concern: covered.
2. Expanded `presentation_profile` and preference model exists: covered.
3. Profile context is stored in `localStorage` and backend session: covered.
4. Profile context is normalized and validated by separate services: covered.
5. Profile clarification is soft and contextual: covered.
   This now includes concrete runtime questions for presentation direction and
   wearable-versus-expressive preference, not only silhouette preference.
6. `ProfileStyleAlignmentService` exists: covered.
7. Reasoning receives profile-aligned style bundle: covered.
8. `FashionBrief` contains profile-derived decisions: covered.
   This includes silhouette-aware anti-repeat constraints from recent history.
9. Prompt / generation pipeline receives normalized profile constraints: covered.
   This now includes active use during prompt compilation, not only passive
   storage in generation payload metadata.
10. Missing profile does not break runtime: covered.
11. Architecture is ready for future persistent profile: covered.
12. Unit, integration, and product tests exist: covered.

---

## Section 28 Definition of Done

- Bot is no longer structurally “one-size-fits-all”: covered.
- Profile context is an explicit runtime layer: covered.
- Reasoning works against user-specific stylistic framing: covered.
- Parser-upgraded style knowledge is aligned against profile before reasoning: covered.
- Recommendations and visualization are more profile-relevant by architecture: covered.
- Profile model remains extensible for future preference fields: covered.

---

## Residual Note

No open code-level Stage 4 gaps were found after the backend session-storage,
retrieval-weighting, and silhouette anti-repeat passes.

The only remaining limitation in this audit is procedural:
- frontend product tests exist but were not executed locally because the frontend
  runtime dependencies are not installed in this environment.
