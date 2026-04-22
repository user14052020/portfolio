# Style Enrichment Runtime Policy And UI Plan Audit

Audit date: 2026-04-21

Source plan:
`docs/upd/0-parser/style_enrichment_runtime_policy_and_ui_plan_full.md`

Scope:
- section 31 implementation substeps
- section 32 acceptance criteria
- section 33 definition of done
- section 34 architectural outcome

Note:
- Builds were intentionally not run.
- Tests were intentionally not run.
- This audit maps implemented files and contract coverage to the plan.

---

## Section 31 Implementation Substeps

1. Facet tables and migration: covered.
   Evidence: `202604170001_style_enrichment_facets_layer.py`,
   `apps/backend/app/models/style_*_facets.py`, and `StyleLlmEnrichment`.

2. ChatGPT enrichment service: covered.
   Evidence: `style_chatgpt_enrichment_service.py`, prompt builder,
   OpenAI adapter, `StyleEnrichmentPayload`, and DB writer.

3. Batch/backfill runner: covered.
   Evidence: `style_chatgpt_batch_runner.py` and `run_style_enrichment.py`.
   Covered paths include single style, batch, dry run, skip existing, and overwrite.

4. Enriched data in runtime: covered.
   Evidence: `PromptPipelineBuilder`, `FashionBriefBuilder`,
   and `test_enriched_runtime_consumption_integration.py`.

5. Generation style explanation: covered.
   Evidence: backend DTO in `generation_job.py`, `GenerationService`,
   and frontend `GenerationStyleExplanation`.

6. Runtime settings layer: covered.
   Evidence: `StylistRuntimeSettingsService`,
   `202604180001_stylist_runtime_settings_in_site_settings.py`,
   API route, and admin manager UI.

7. Non-admin limits: covered.
   Evidence: `UsageAccessPolicyService`, generation API enforcement,
   stylist enforcement, and runtime policy tests.

8. Cooldown: covered.
   Evidence: `InteractionThrottleService`, `ChatCooldownSendControl`,
   composer/quick-action locks, and cooldown enforcement tests.

9. Rounded UI polish: covered.
   Evidence: `StylistChatPanel`, `ChatThread`, `InputSurface`, `SoftButton`,
   generation surfaces, and rounded UI product contract test.

10. Observability and tests: covered.
    Evidence: enrichment observability helpers, runtime policy observability,
    unit tests, integration tests, product tests, and architecture tests.

---

## Section 32 Acceptance Criteria

1. Current parser is not fully rewritten or broken: covered.
   Existing parser/ingestion pipeline remains in place.
   Enrichment is layered through a separate service and facet persistence.

2. Separate enrichment script/service reads source text from DB: covered.
   Evidence: `_load_source_material` and `run_style_enrichment.py`.

3. Enrichment sends text to ChatGPT and receives structured JSON: covered.
   Evidence: OpenAI adapter, prompt builder, and enrichment completion handling.

4. JSON validates and writes to separate tables: covered.
   Evidence: `StyleEnrichmentPayload`, payload mapper, facet models, and writer path.

5. Data is used in consultation and image generation: covered.
   Evidence: `FashionBriefBuilder`, `GenerationPayloadBuilder`,
   and runtime consumption integration tests.

6. Generation shows style explanation near generated image: covered.
   Evidence: result card/surface placement and frontend contract tests.

7. Non-admin limits work: covered.
   Evidence: `UsageAccessPolicyService`, generation API, stylist enforcement,
   and policy tests.

8. Limits change from admin: covered.
   Evidence: `stylist_runtime_settings` route, admin manager, and settings tests.

9. Cooldown after send and try-other-style works: covered.
   Evidence: throttle service, frontend lock behavior, and backend enforcement test.

10. Cooldown value changes from admin: covered.
    Evidence: runtime settings service, API, and admin UI payload contract.

11. Chat UI is rounded and uses circular loader/countdown: covered.
    Evidence: rounded UI contract test, `ChatCooldownSendControl`, and `ProgressRing`.

12. Fallback exists when enrichment has not run: covered.
    Evidence: existing runtime fallback paths and invalid JSON fallback tests.

13. Architecture remains clean and extensible: covered.
    Evidence: constructor injection in `StylistService` and architecture contract tests.

---

## Section 33 Definition Of Done

- Richer style knowledge without full parser rewrite: covered.
- Enrichment improves consultation and generation: covered.
- Generation results are more explainable: covered.
- Quotas and cooldown are admin-managed: covered.
- UX is softer and more modern: covered.
- Backend enforcement protects against UI bypass: covered.
- Solution avoids architecture chaos and remains scalable: covered.

---

## Section 34 Architectural Outcome

### Ingestion/Data Layer

- Existing parser remains the stable base: covered.
  Evidence: enrichment is implemented as a separate layer over existing ingestion code.

- ChatGPT-based enrichment layer exists: covered.
  Evidence: `DefaultStyleChatGptEnrichmentService`,
  `DefaultStyleChatGptEnrichmentBatchRunner`, and `run_style_enrichment.py`.

- Richer style data is stored in separate tables: covered.
  Evidence: style enrichment facet migration and `style_*_facets.py` models.

### Runtime

- Text consultation becomes smarter: covered.
  Evidence: enriched facet metadata flows through `FashionBriefBuilder`
  and `PromptPipelineBuilder`.

- Generation becomes more precise: covered.
  Evidence: `GenerationPayloadBuilder`, visual generation plan metadata,
  and generation consistency product tests.

- Generation has understandable style explanation: covered.
  Evidence: `GenerationStyleExplanation`, generation DTO fields, and contract tests.

### Product Policy

- Non-admin usage is limited: covered.
  Evidence: `UsageAccessPolicyService` and backend enforcement tests.

- Cooldown and quotas are centralized: covered.
  Evidence: `StylistRuntimeSettingsService`, `UsageAccessPolicyService`,
  and `InteractionThrottleService`.

- Settings change through admin without redeploy: covered.
  Evidence: `stylist_runtime_settings` API and `StylistRuntimeSettingsManager`.

### UI

- Chat becomes softer and more premium: covered.
  Evidence: rounded shell, surfaces, message bubbles, chips, and generation cards.

- Interaction looks intentional instead of technical: covered.
  Evidence: circular countdown, disabled interaction states, and product contract tests.

---

## Residual Risk

- This audit is static and contract-based because builds and tests were skipped.
- Runtime validation should be done separately when test execution is allowed.
