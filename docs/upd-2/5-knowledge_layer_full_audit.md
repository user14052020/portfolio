# Knowledge Layer Plan Audit

Audit date: 2026-05-01

Source plan:
`docs/upd-2/5-knowledge_layer_full.md`

Scope:
- section 20 admin flags and provider control
- section 21 application services
- section 23 observability
- section 24 testing
- section 25 clean architecture / SOLID
- section 26 implementation substeps
- section 27 acceptance criteria
- section 28 definition of done
- critical behavior from sections 1-19

Note:
- Builds were intentionally not run.
- Backend knowledge-layer regressions were run.
- Route files were syntax-checked locally.
- Full FastAPI route import/execution was not run locally because the current
  Python environment does not include `fastapi`.

Executed verification:
- `python -B -m unittest tests/test_preview_knowledge_retrieval.py tests/test_knowledge_runtime_settings.py tests/test_knowledge_context_assembler.py tests/test_knowledge_providers_registry.py tests/test_style_distilled_knowledge_provider.py tests/test_knowledge_retrieval_service.py tests/test_knowledge_bundle_builder.py tests/test_knowledge_layer_e2e.py tests/test_knowledge_ranker.py tests/test_reasoning_pipeline_contracts.py tests/test_reasoning_pipeline_orchestration_adapter.py tests/test_stylist_orchestrator.py`
- Result: `Ran 113 tests`, `OK`
- `python -m py_compile app/api/routes/stylist_chat.py app/api/routes/knowledge_runtime_settings.py app/schemas/stylist.py app/schemas/knowledge_runtime_settings.py app/application/knowledge/use_cases/preview_knowledge_retrieval.py app/application/knowledge/services/knowledge_providers_registry.py`
- Result: `OK`

---

## Section 26 Implementation Substeps

1. Update knowledge contracts: covered.
   Evidence:
   `apps/backend/app/domain/knowledge/entities/knowledge_query.py`,
   `apps/backend/app/domain/knowledge/entities/knowledge_card.py`,
   `apps/backend/app/domain/knowledge/entities/knowledge_provider_config.py`,
   `apps/backend/app/domain/reasoning/entities/knowledge_context.py`,
   `apps/backend/app/domain/knowledge/enums/knowledge_type.py`.

   Covered behavior includes richer query fields, richer card metadata,
   expanded taxonomy, runtime flags, and typed `KnowledgeContext`.

2. Implement `StyleFacetKnowledgeProjector`: covered.
   Evidence:
   `apps/backend/app/application/knowledge/services/style_facet_knowledge_projector.py`,
   `apps/backend/app/domain/knowledge/entities/knowledge_document.py`,
   `apps/backend/app/domain/knowledge/entities/knowledge_chunk.py`,
   `apps/backend/app/domain/knowledge/entities/style_knowledge_projection_result.py`.

   Covered behavior includes facet -> document/chunk/card projection,
   projection versioning, parser version propagation, and compatibility
   fallback runtime cards.

3. Implement `StyleDistilledKnowledgeProvider`: covered.
   Evidence:
   `apps/backend/app/infrastructure/knowledge/style_distilled_knowledge_provider.py`,
   `apps/backend/app/infrastructure/knowledge/repositories/style_catalog_repository.py`.

   Covered behavior includes runtime retrieval from semantic-distilled style
   knowledge, relevance gating by query mode/profile, and fallback to legacy
   summary/runtime cards when richer projected cards are absent.

4. Update `KnowledgeProvidersRegistry`: covered.
   Evidence:
   `apps/backend/app/application/knowledge/services/knowledge_providers_registry.py`,
   `apps/backend/app/domain/knowledge/entities/knowledge_runtime_flags.py`,
   `apps/backend/app/domain/knowledge_runtime_settings.py`.

   Covered behavior includes:
   - `style_ingestion` pinned as first canonical runtime provider
   - feature-flag gating
   - persisted priority overrides
   - graceful degradation
   - duplicate/disabled provider skipping

5. Implement `KnowledgeContextAssembler`: covered.
   Evidence:
   `apps/backend/app/application/knowledge/services/knowledge_context_assembler.py`.

   Covered behavior includes:
   - multi-provider retrieval
   - de-duplication
   - typed context shaping
   - `retrieval_profile` passthrough
   - style / advice / visual / history / editorial buckets
   - retrieval observability trace

6. Add `KnowledgeCardRanker`: covered.
   Evidence:
   `apps/backend/app/application/knowledge/services/knowledge_ranker.py`.

   Covered behavior includes ranking by:
   - relevance
   - diversity
   - provider priority

7. Integrate with reasoning / profile / voice: covered.
   Evidence:
   - `apps/backend/app/application/reasoning/services/fashion_reasoning_context_assembler.py`
   - `apps/backend/app/application/reasoning/services/fashion_reasoner.py`
   - `apps/backend/app/application/reasoning/services/voice_layer_composer.py`
   - `apps/backend/app/application/reasoning/services/reasoning_output_mapper.py`
   - `apps/backend/app/services/stylist_orchestrator.py`

   Covered behavior includes central `KnowledgeContext` assembly, profile-aware
   retrieval shaping, typed voice hints, and runtime-flag gating all the way
   into voice output.

8. Add observability and tests: covered.
   Evidence:
   - `apps/backend/app/application/knowledge/services/knowledge_context_assembler.py`
   - `apps/backend/app/application/reasoning/services/fashion_reasoning_pipeline.py`
   - `apps/backend/app/application/stylist_chat/orchestrator/stylist_chat_orchestrator.py`
   - test files listed in verification

---

## Critical Coverage From Sections 1-19

### `style_ingestion` as semantic-distilled first canonical provider

- Covered.
  `style_ingestion` is now the first strong canonical provider in runtime
  ordering, built on semantic-distilled projections rather than coarse legacy
  style tables alone.

### Knowledge layer is a typed provider-oriented abstraction, not a text table

- Covered.
  Runtime logic works with `KnowledgeQuery`, `KnowledgeCard`,
  `KnowledgeProviderConfig`, `KnowledgeContext`, projection entities,
  and provider protocols instead of raw parser SQL or generic text buckets.

### Parser upgrade is consumed downstream

- Covered.
  Semantic fragments, style facets, visual facets, relation facets, and
  projected style cards are all consumed downstream by reasoning, profile
  alignment, voice composition, and generation handoff.

### Central `KnowledgeContext` instead of parser-table reads

- Covered.
  The reasoning runtime now reads `KnowledgeContext` from a central knowledge
  layer path rather than reading parser tables directly.

### Runtime-safe provider abstraction for future expansion

- Covered.
  Registry, ranker, assembler, runtime settings, and provider contracts allow
  future Malevich / historian / stylist sources to be added without rewriting
  the reasoning core.

### Feature flags and provider control

- Covered.
  Runtime flags exist for:
  - `style_ingestion_enabled`
  - `malevich_enabled`
  - `fashion_historian_enabled`
  - `stylist_enabled`
  - `use_editorial_knowledge`
  - `use_historical_context`
  - `use_color_poetics`

  They are now read in:
  - `KnowledgeProvidersRegistry`
  - `FashionReasoningContextAssembler`
  - `FashionReasoner`
  - `VoiceLayerComposer`

  Importantly, this is covered not only at class level but on the live
  orchestrator runtime path through
  `DatabaseKnowledgeRuntimeSettingsProvider`.

### Admin/runtime settings repository

- Covered.
  Evidence:
  - `apps/backend/app/models/site_settings.py`
  - `apps/backend/app/repositories/site_settings.py`
  - `apps/backend/app/services/knowledge_runtime_settings.py`
  - `apps/backend/alembic/versions/202605010001_knowledge_runtime_settings_in_site_settings.py`

  Persisted settings now store runtime flags and provider priority overrides.

### Interface-layer admin / diagnostics / debug DTOs

- Covered.
  Evidence:
  - `apps/backend/app/api/routes/knowledge_runtime_settings.py`
  - `apps/backend/app/api/routes/stylist_chat.py`
  - `apps/backend/app/schemas/knowledge_runtime_settings.py`
  - `apps/backend/app/schemas/stylist.py`
  - `apps/backend/app/application/knowledge/use_cases/preview_knowledge_retrieval.py`

  Covered behavior includes:
  - admin settings endpoints
  - diagnostics endpoint for current runtime flags and enabled providers
  - retrieval debug DTO returning `KnowledgeQuery`, central `KnowledgeContext`,
    context counts, observability trace, runtime flags, provider priorities,
    and enabled provider order

---

## Section 20 Admin Flags And Provider Control

### 20.1 What should be available from admin

- Covered.
  Admin runtime settings now allow:
  - enabling/disabling providers
  - adjusting provider priority overrides
  - enabling/disabling reasoning layers
  - safe diagnostics of runtime provider state

### 20.2 Minimal flags

- Covered exactly.
  All seven flags from the plan exist in domain settings, persisted settings,
  and runtime diagnostics output.

### 20.3 Where flags are applied

- Covered literally.
  Flags are read in all four required places:
  - `KnowledgeProvidersRegistry`
  - `FashionReasoningContextAssembler`
  - `FashionReasoner`
  - `VoiceLayerComposer`

---

## Section 23 Observability

### 23.1 Retrieval run observability

- Covered.
  Current retrieval observability includes:
  - query mode
  - retrieval profile
  - providers used
  - cards returned per provider
  - cards filtered out
  - empty providers
  - provider latency
  - ranking summary / decisions

### 23.2 Style-provider-specific observability

- Covered.
  Current observability includes:
  - projected cards count
  - emitted knowledge types
  - low-richness styles
  - legacy summary fallback styles
  - projection versions
  - parser versions

### 23.3 Why this matters

- Covered by implementation.
  Current telemetry can explain:
  - why context was poor
  - why a provider returned little or nothing
  - where knowledge cards were filtered out
  - whether parser-upgraded projection is actually feeding runtime

---

## Section 24 Testing

### 24.1 Unit tests

- Covered.
  Evidence:
  - `tests/test_knowledge_layer_contracts.py`
  - `tests/test_style_facet_knowledge_projector.py`
  - `tests/test_style_distilled_knowledge_provider.py`
  - `tests/test_knowledge_providers_registry.py`
  - `tests/test_knowledge_context_assembler.py`
  - `tests/test_knowledge_ranker.py`
  - `tests/test_knowledge_runtime_settings.py`
  - `tests/test_preview_knowledge_retrieval.py`

### 24.2 Integration tests

- Covered.
  Evidence:
  - `tests/test_knowledge_retrieval_service.py`
  - `tests/test_knowledge_layer_e2e.py`
  - `tests/test_reasoning_pipeline_contracts.py`
  - `tests/test_reasoning_pipeline_orchestration_adapter.py`
  - `tests/test_stylist_orchestrator.py`

  Covered scenarios include:
  - style provider only
  - style provider + empty editorial providers
  - style provider + future historian provider
  - parser facets -> cards -> reasoning retrieval
  - feature flags on/off
  - graceful degradation
  - runtime settings provider overriding static flags
  - canonical style-provider ordering under dynamic priority overrides

### 24.3 Product tests

- Covered at backend runtime behavior level.
  Current regressions explicitly check that:
  - reasoner becomes richer with central knowledge context
  - visual CTA becomes more relevant through richer knowledge/image context
  - historical / editorial / color-poetic layers activate only when allowed
  - missing providers do not break runtime

---

## Section 25 Clean Architecture / SOLID

### 25.1 Domain layer

- Covered.
  `KnowledgeQuery`, `KnowledgeCard`, `KnowledgeContext`,
  `KnowledgeProviderConfig`, `KnowledgeRuntimeFlags`,
  and projection/result entities live in domain.

### 25.2 Application layer

- Covered.
  `StyleFacetKnowledgeProjector`, `KnowledgeProvidersRegistry`,
  `KnowledgeContextAssembler`, `KnowledgeCardRanker`,
  and preview/query use cases exist as separate application-layer units.

### 25.3 Infrastructure layer

- Covered.
  Repositories, provider adapters, projector persistence adapters,
  and admin settings persistence are in infrastructure/services.

### 25.4 Interface layer

- Covered.
  Admin endpoints, diagnostics endpoints, and retrieval debug DTOs now exist.

### 25.5 SOLID accents

- Covered.
  SRP:
  provider fetch, projection, assembly, ranking, settings persistence, and
  debug preview are separated.

  OCP:
  future providers are added by extension through provider contracts and
  registry wiring.

  DIP:
  reasoning and voice paths depend on `KnowledgeContext` and provider/settings
  interfaces rather than parser SQL details.

---

## Section 27 Acceptance Criteria

1. Knowledge layer no longer depends on coarse style profile only: covered.
2. `style_ingestion` works as semantic-distilled provider: covered.
3. Parser-upgraded style facets project into documents/chunks/cards: covered.
4. Reasoning pipeline receives `KnowledgeContext` instead of parser DB reads: covered.
5. Profile alignment works with runtime knowledge bundles, not raw tables: covered.
6. Graceful degradation works with empty editorial providers: covered.
7. Feature flags can enable/disable providers without redeploy: covered at code level through persisted site settings and runtime provider resolution.
8. New knowledge types cover visual language, styling rules, props, relations, and image composition: covered.
9. Future providers can be added without rewriting the core: covered architecturally.
10. Unit, integration, and product-level regressions exist: covered.

---

## Section 28 Definition Of Done

- Knowledge layer is now a shared typed runtime abstraction: covered.
- Parser upgrade is fully used downstream: covered.
- `style_ingestion` is the first strong canonical provider: covered.
- Reasoning, profile, and voice do not depend directly on parser SQL details: covered.
- System is ready for safe expansion by new knowledge sources: covered architecturally.
- Future Malevich / historian / stylist integration can be evolutionary rather than a rewrite: covered.

---

## Residual Note

- This audit finds no remaining code-level functional gaps against the current
  literal Stage 5 plan sections above.
- The remaining local verification caveat is interface execution:
  route syntax is checked, but live FastAPI route import/execution was not run
  in this environment because `fastapi` is absent locally.
- Builds were intentionally skipped as requested.
