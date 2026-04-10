
# Этап 9. Усилить ComfyUI pipeline

## Контекст этапа

В основном архитектурном плане проекта Этап 9 сформулирован как усиление **ComfyUI pipeline**. В плане прямо зафиксировано, что даже отличный prompt будет давать похожие картинки, если workflow слишком жёсткий, поэтому нужно:
- добавить управляемые `visual presets`;
- ввести параметры `background families`, `spacing density`, `object count range`, `camera distance`, `shadow hardness`, `layout archetype`;
- использовать разные presets для разных режимов:
  - `garment_matching` — `anchor garment centrality high`
  - `style_exploration` — `diversity high`
  - `occasion_outfit` — `practical coherence high`
- сохранять метаданные генерации:
  - `final prompt`
  - `negative prompt`
  - `seed`
  - `style id`
  - `visual preset`
  - `palette tags`
  - `garments tags`

Этот этап также должен быть связан с уже существующим Этапом 0 — parser / ingestion pipeline, который наполняет базу стилей подробными данными, и с Этапом 8, где knowledge layer начинает использовать эти данные как runtime source-of-truth.

То есть Stage 9 нельзя проектировать как "немного подкрутить workflow". Это должен быть **управляемый visual generation layer**, который:
- получает осмысленный structured brief;
- использует style knowledge из базы;
- учитывает anti-repeat и diversity constraints;
- управляет вариативностью Comfy не случайно, а через доменные параметры.

---

# 1. Цель этапа

Сделать так, чтобы ComfyUI pipeline перестал быть жёстким и слабо управляемым блоком, который:
- даёт похожие результаты даже при хороших промптах;
- не знает, какой режим чата его вызвал;
- не использует knowledge layer;
- не сохраняет достаточно данных для диагностики.

После Stage 9 система должна:
- использовать mode-aware visual presets;
- уметь менять композицию, поверхность, плотность, визуальный темп и раскладку осмысленно;
- принимать structured generation payload, а не только длинный prompt;
- использовать стиль и knowledge traits из базы, наполняемой parser’ом;
- быть анализируемой по логам и метаданным;
- быть готовой к росту количества workflows и preset families.

---

# 2. Архитектурная проблема текущего ComfyUI слоя

Даже после улучшения orchestrator, knowledge layer и prompt builder можно всё равно получить слабый визуальный результат, если Comfy pipeline:

1. использует один и тот же layout archetype;
2. держит почти фиксированную surface/background logic;
3. не различает mode-specific generation goals;
4. не умеет использовать diversity constraints;
5. не знает, что такое `anchor garment centrality`;
6. не умеет различать practical outfit image и exploratory stylistic spread;
7. не сохраняет метаданные для анализа повторов.

В основном плане это прямо обозначено: prompt сам по себе не решает проблему, если workflow слишком жёсткий. Поэтому ComfyUI должен стать управляемым отдельным слоем. 

---

# 3. Архитектурные принципы реализации

## 3.1. Clean Architecture

### Domain layer
Содержит:
- `VisualPreset`
- `VisualGenerationIntent`
- `CompositionProfile`
- `GenerationMetadata`
- `SurfaceFamily`
- `LayoutArchetype`
- `CameraProfile`
- `ShadowProfile`

### Application layer
Содержит:
- `VisualPresetResolver`
- `GenerationPayloadAssembler`
- `ComfyWorkflowSelector`
- `ComfyGenerationOrchestrator`
- `GenerationMetadataRecorder`

### Infrastructure layer
Содержит:
- ComfyUI client
- workflow template repository
- preset registry
- image generation adapters
- metadata persistence
- queue worker integration

### Interface layer
Содержит:
- internal DTO between prompt builder and generation worker
- debug/admin views for preset and generation metadata
- status/result serializers

## 3.2. SOLID

### Single Responsibility
- preset resolver выбирает preset;
- payload assembler собирает mode-aware payload;
- workflow selector выбирает workflow version/template;
- Comfy adapter только отправляет payload в ComfyUI;
- metadata recorder только сохраняет artefacts и traces.

### Open/Closed
Новый visual preset, background family или workflow template добавляется без переписывания chat orchestrator.

### Liskov
Любой generation backend adapter должен быть взаимозаменяем:
- `ComfyGenerationAdapter`
- `MockGenerationAdapter`
- будущий `AlternativeImageBackendAdapter`

### Interface Segregation
Нужны отдельные интерфейсы:
- `VisualPresetResolver`
- `WorkflowSelector`
- `GenerationPayloadAssembler`
- `GenerationBackendAdapter`
- `GenerationMetadataStore`

### Dependency Inversion
Application layer зависит от абстракций generation backend, а не от конкретного Comfy endpoint или workflow JSON.

## 3.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    visual_generation/
      entities/
      value_objects/
      enums/
      policies/
  application/
    visual_generation/
      services/
        visual_preset_resolver.py
        workflow_selector.py
        generation_payload_assembler.py
        generation_metadata_recorder.py
      use_cases/
        build_visual_generation_plan.py
        run_generation_job.py
        persist_generation_result.py
  infrastructure/
    comfy/
      client/
      workflows/
      presets/
      adapters/
    persistence/
      repositories/
  interfaces/
    api/
      serializers/
      admin/
```

---

# 4. Связь с уже существующим parser / ingestion pipeline

Это ключевая поправка относительно абстрактного Stage 9.

## 4.1. Parser уже наполняет style data
Этап 0 и детальный ingestion-документ фиксируют, что parser уже:
- тянет style pages через MediaWiki API;
- нормализует summary, palette, garments, materials, silhouettes, moods, relations;
- пишет их в нормализованные таблицы;
- строит taxonomy links и style relations;
- поддерживает source-level jobs, versioning и metadata. 

Значит Comfy pipeline не должен жить как полностью “слепой” визуальный блок.

## 4.2. Что это означает practically
Comfy pipeline должен получать из upstream не только `prompt`, но и:
- `style_id`
- `style_name`
- `palette`
- `materials`
- `garment_list`
- `style_family`
- `historical_reference`
- `composition_rules`
- `diversity_constraints`
- `flatlay pattern hints`

То есть visual layer должен стать downstream consumer уже существующего ingestion + knowledge stack.

## 4.3. Ключевой принцип
Parser = upstream supplier knowledge  
Knowledge layer = runtime retrieval  
Prompt builder = semantic compiler  
Comfy pipeline = visual realization layer

Нельзя проектировать Comfy pipeline так, будто style DB не существует.

---

# 5. Связь Stage 9 с предыдущими этапами

## 5.1. Связь с Этапом 3
Explicit orchestrator должен вызывать generation не просто с prompt string, а с structured generation plan.

## 5.2. Связь с Этапами 4 и 5
- `garment_matching` должен передавать `anchor garment centrality`
- `occasion_outfit` должен передавать `practical coherence` и occasion suitability

## 5.3. Связь с Этапом 6
`style_exploration` должен передавать:
- persistent style history
- diversity constraints
- desired semantic / visual distance

## 5.4. Связь с Этапом 7
Новый `FashionBrief` из Stage 7 становится главным входом для Comfy generation pipeline.

## 5.5. Связь с Этапом 8
Knowledge layer поставляет:
- style catalog data
- color theory notes
- tailoring notes
- flatlay prompt patterns
которые влияют на visual preset и workflow configuration.

---

# 6. Новый центральный объект: VisualGenerationPlan

Prompt builder не должен отправлять в Comfy просто строку prompt.  
Нужен отдельный domain/application объект:

```python
class VisualGenerationPlan(BaseModel):
    mode: str
    style_id: str | None = None
    style_name: str | None = None
    fashion_brief_hash: str | None = None
    final_prompt: str
    negative_prompt: str
    visual_preset_id: str | None = None
    workflow_name: str
    layout_archetype: str | None = None
    background_family: str | None = None
    object_count_range: str | None = None
    spacing_density: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    anchor_garment_centrality: str | None = None
    practical_coherence: str | None = None
    diversity_profile: dict = {}
    palette_tags: list[str] = []
    garments_tags: list[str] = []
    materials_tags: list[str] = []
    metadata: dict = {}
```

## Почему это важно
Без `VisualGenerationPlan`:
- workflow parameters неотделимы от prompt string;
- mode-specific визуальная логика неуправляема;
- нельзя объяснимо менять layout/spacing/background;
- нельзя тестировать Comfy integration отдельно от reasoning.

---

# 7. Visual presets как first-class concept

## 7.1. Что такое visual preset
`VisualPreset` — это не просто "рандомная сцена", а контролируемый набор визуальных параметров, влияющих на:
- поверхность;
- композицию;
- расстояние камеры;
- плотность раскладки;
- жёсткость теней;
- расстановку предметов;
- вес центрального элемента.

## 7.2. Рекомендуемая модель

```python
class VisualPreset(BaseModel):
    id: str
    name: str
    mode_affinity: list[str] = []
    background_family: str | None = None
    layout_archetype: str | None = None
    spacing_density: str | None = None
    object_count_range: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    anchor_garment_centrality: str | None = None
    practical_coherence: str | None = None
    diversity_bias: str | None = None
    tags: list[str] = []
```

## 7.3. Почему presets нужны
Потому что один и тот же semantic prompt при разных presets может давать:
- editorial flat lay;
- airy catalog spread;
- practical outfit layout;
- minimal product-like composition.

Это и есть то, что в плане называется управляемыми visual presets.

---

# 8. Preset families, указанные в основном плане

Основной план прямо требует управлять следующими параметрами:
- `background families`
- `spacing density`
- `object count range`
- `camera distance`
- `shadow hardness`
- `layout archetype`

Именно эти параметры должны стать частью preset registry.

## 8.1. Background families
Примеры:
- neutral paper
- off-white linen
- warm wood
- cool stone
- dark textured surface
- muted studio background

## 8.2. Spacing density
Примеры:
- compact
- balanced
- airy

## 8.3. Object count range
Примеры:
- minimal capsule
- balanced outfit set
- rich layered spread

## 8.4. Camera distance
Примеры:
- tight overhead
- medium flat lay
- wider editorial overhead

## 8.5. Shadow hardness
Примеры:
- soft diffused
- moderate natural
- crisp editorial

## 8.6. Layout archetype
Примеры:
- centered anchor composition
- diagonal editorial spread
- radial outfit spread
- catalog grid-like arrangement
- practical dressing board

---

# 9. Mode-aware visual behavior

## 9.1. `garment_matching`
План прямо требует: `anchor garment centrality high`.

### Что это означает
- anchor garment должен быть визуально главным;
- layout должен строиться вокруг центральной вещи;
- остальные элементы подчинены ей;
- object count должен быть умеренным;
- visual clutter должен быть низким.

### Preset strategy
- centered anchor composition
- medium object count
- balanced spacing
- clear silhouette visibility
- lower experimentation

## 9.2. `style_exploration`
План прямо требует: `diversity high`.

### Что это означает
- больше variation по preset selection;
- больше visual preset shifts;
- controlled experimentation;
- не повторять previous composition/background/layout.

### Preset strategy
- rotating preset families
- explicit anti-repeat on visual layer
- broader layout archetype pool
- dynamic object count / spacing profiles

## 9.3. `occasion_outfit`
План прямо требует: `practical coherence high`.

### Что это означает
- образ должен восприниматься как носибельный и уместный;
- композиция должна быть читаемой;
- вещный состав должен выглядеть как coherent outfit.

### Preset strategy
- practical dressing board
- lower noise
- realistic combination emphasis
- moderate spread, not overly conceptual

---

# 10. VisualPresetResolver

## 10.1. Основной контракт

```python
class VisualPresetResolver(Protocol):
    async def resolve(
        self,
        mode: str,
        fashion_brief: dict,
        style_history: list[dict] | None = None,
        diversity_constraints: dict | None = None,
    ) -> VisualPreset:
        ...
```

## 10.2. Ответственность
Он должен:
- выбрать preset на основе mode;
- учитывать diversity constraints;
- учитывать style history;
- учитывать occasion / anchor garment context;
- избегать recent visual collisions.

## 10.3. Что он не делает
- не генерирует image prompt;
- не решает style identity;
- не вызывает ComfyUI;
- не пишет в БД напрямую.

---

# 11. WorkflowSelector

## 11.1. Зачем нужен
Разные режимы и presets могут требовать разных Comfy workflow templates или разных конфигураций одного workflow.

## 11.2. Основной контракт

```python
class WorkflowSelector(Protocol):
    async def select(
        self,
        mode: str,
        visual_preset: VisualPreset,
        fashion_brief: dict,
    ) -> str:
        ...
```

## 11.3. Примеры сценариев
- один workflow для fashion flatlay base
- отдельный workflow template для exploratory mode
- отдельный workflow branch для practical outfit layout

Важно:
workflow selection должен быть отдельным слоем, а не зашитым внутри route/worker if/else.

---

# 12. GenerationPayloadAssembler

## 12.1. Что он делает
Из `FashionBrief`, `CompiledImagePrompt` и `VisualPreset` он собирает полный `VisualGenerationPlan` и затем backend-specific payload.

## 12.2. Вход
- structured fashion brief
- compiled image prompt
- visual preset
- workflow selection
- diversity constraints
- style metadata from knowledge layer

## 12.3. Выход
- `VisualGenerationPlan`
- backend payload for ComfyUI
- metadata package for persistence

---

# 13. Использование parser/knowledge data в Comfy pipeline

Это ключевое требование для новой версии Stage 9.

## 13.1. Что должно влиять на Comfy pipeline из ingestion-базы
Из parser/knowledge layer в Comfy визуальный слой должны доходить:
- `style_family`
- `palette`
- `materials`
- `garment_list`
- `style traits`
- `flatlay pattern hints`
- `style taxonomy`
- `relations / nearby styles`
- anti-mix / negative notes

## 13.2. Примеры использования
### `style_exploration`
Если parser сохранил, что стиль:
- принадлежит family X,
- типично использует muted palette,
- характерен relaxed silhouette,
- имеет specific accessories,

то visual preset resolver и payload assembler:
- не просто строят prompt,
- а подбирают visual composition, подходящую этому style identity.

### `garment_matching`
Если knowledge layer даёт:
- compatible materials,
- color pairing,
- outfit balancing,
- silhouette notes,

то Comfy pipeline может использовать:
- более practical layout,
- адекватный object count,
- restrained background family.

### `occasion_outfit`
Если retrieval возвращает:
- event fit,
- dress-code logic,
- season/material notes,

то visual pipeline должен не делать overly conceptual spread, а усиливать practical coherence.

---

# 14. Anti-repeat на уровне Comfy pipeline

Этап 6 ввёл anti-repeat на semantic и visual уровнях. Stage 9 должен довести это до image backend.

## 14.1. Что именно должно доходить
- `avoid previous palette`
- `avoid previous composition layout`
- `avoid previous background family`
- `force material contrast`
- `force visual preset shift`
- `force spacing change`
- `force camera distance change`

## 14.2. Где это должно применяться
Не только в prompt text, но и в:
- preset resolution
- workflow parameter selection
- generation metadata
- post-generation analysis

## 14.3. Почему это критично
Если anti-repeat остаётся только в prompt string, Comfy workflow всё равно может продолжать выдавать одинаковую сцену.

---

# 15. Generation metadata must become first-class

Основной план прямо требует сохранять метаданные генерации:
- final prompt
- negative prompt
- seed
- style id
- visual preset
- palette tags
- garments tags

Этап 9 должен расширить это до полноценного generation trace.

## 15.1. Рекомендуемая модель

```python
class GenerationMetadata(BaseModel):
    generation_job_id: str
    mode: str
    style_id: str | None = None
    style_name: str | None = None
    fashion_brief_hash: str | None = None
    compiled_prompt_hash: str | None = None
    final_prompt: str
    negative_prompt: str
    seed: int | None = None
    workflow_name: str
    workflow_version: str | None = None
    visual_preset_id: str | None = None
    background_family: str | None = None
    layout_archetype: str | None = None
    spacing_density: str | None = None
    camera_distance: str | None = None
    shadow_hardness: str | None = None
    palette_tags: list[str] = []
    garments_tags: list[str] = []
    materials_tags: list[str] = []
    diversity_constraints: dict = {}
    knowledge_refs: list[str] = []
```

## 15.2. Зачем это нужно
- анализировать повторы;
- воспроизводить генерации;
- мерить quality drift;
- понимать, где ломается pipeline;
- строить admin/debug инструменты.

---

# 16. Новая роль Comfy worker / generation worker

Stage 10 позже вводит полноценные generation jobs и очереди, но Stage 9 уже должен готовить Comfy слой к этому.

## 16.1. Worker должен принимать structured plan
Не просто:
- prompt string
- seed

А:
- `VisualGenerationPlan`
- workflow template
- preset config
- metadata package

## 16.2. Worker не должен сам “догадываться”
Он не должен:
- выбирать style
- выбирать preset
- решать diversity
- определять occasion fit

Это всё должно приходить сверху из application layer.

---

# 17. Связь Stage 9 со Stage 10

Stage 9 готовит visual generation architecture, а Stage 10 формализует это как queue/job layer.

То есть после Stage 9 generation job уже должна быть conceptually такой:

```text
API route
→ orchestrator
→ fashion brief
→ compiled image prompt
→ visual preset resolution
→ workflow selection
→ VisualGenerationPlan
→ enqueue generation job
→ worker executes plan in ComfyUI
→ metadata persisted
```

---

# 18. Frontend и Comfy pipeline

Frontend не должен знать детали Comfy, но в результате Stage 9 он сможет:
- показывать более осмысленные loading states;
- отображать, какой visual preset был использован;
- в admin/debug режиме показывать:
  - palette tags
  - garments tags
  - preset id
  - workflow name
  - style id

Это сильно повысит дебажимость и управляемость системы.

---

# 19. Observability

## 19.1. Что логировать
На каждый generation run:
- `session_id`
- `message_id`
- `mode`
- `style_id`
- `fashion_brief_hash`
- `compiled_prompt_hash`
- `workflow_name`
- `visual_preset_id`
- `layout_archetype`
- `background_family`
- `camera_distance`
- `spacing_density`
- `seed`
- `generation_job_id`

## 19.2. Метрики
- repeat rate by visual preset
- repeat rate by background family
- repeat rate by layout archetype
- generation success rate per preset
- average generation latency per workflow
- diversity score by mode
- practical coherence score for occasion mode
- anchor garment visibility score for garment mode

---

# 20. Тестирование

## 20.1. Unit tests
Покрыть:
- `VisualPresetResolver`
- `WorkflowSelector`
- `GenerationPayloadAssembler`
- metadata recorder
- anti-repeat propagation to visual layer

## 20.2. Integration tests
Покрыть:
- `garment_matching` chooses anchor-centric preset
- `style_exploration` chooses diversity-aware preset
- `occasion_outfit` chooses practical preset
- parser-derived style traits reach generation plan
- generation metadata persisted correctly

## 20.3. E2E сценарии
Минимальный набор:
1. `garment_matching` → preset with high anchor centrality
2. `style_exploration` twice → different preset/background/layout
3. `occasion_outfit` → practical coherent composition
4. anti-repeat survives until Comfy payload
5. generation metadata allows replay/debug

---

# 21. Рекомендуемая модульная структура

```text
domain/visual_generation/
  entities/
    visual_generation_plan.py
    generation_metadata.py
    visual_preset.py
  value_objects/
    layout_archetype.py
    background_family.py
    camera_profile.py
    shadow_profile.py

application/visual_generation/
  services/
    visual_preset_resolver.py
    workflow_selector.py
    generation_payload_assembler.py
    generation_metadata_recorder.py
  use_cases/
    build_visual_generation_plan.py
    run_generation_job.py
    persist_generation_result.py

infrastructure/comfy/
  client/
    comfy_client.py
  workflows/
    fashion_flatlay_base.json
    garment_matching_variation.json
    style_exploration_variation.json
    occasion_outfit_variation.json
  presets/
    visual_presets_registry.py
  adapters/
    comfy_generation_adapter.py
```

---

# 22. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- считать ComfyUI “тупым чёрным ящиком”, который получает только prompt;
- продолжать жить на одном жёстком workflow без preset abstraction;
- смешивать visual preset selection и prompt builder в одном giant method;
- терять parser/knowledge-derived traits до visual layer;
- делать anti-repeat только на уровне text prompt;
- не сохранять generation metadata;
- зашивать workflow details в domain objects.

---

# 23. Пошаговый план реализации Этапа 9

## Подэтап 9.1. Ввести `VisualPreset` и `VisualGenerationPlan`
Создать центральные domain/application объекты визуального слоя.

## Подэтап 9.2. Реализовать `VisualPresetResolver`
Mode-aware и anti-repeat-aware выбор preset.

## Подэтап 9.3. Реализовать `WorkflowSelector`
Выбор workflow template / branch на основе mode и preset.

## Подэтап 9.4. Реализовать `GenerationPayloadAssembler`
Сбор structured plan и backend payload.

## Подэтап 9.5. Протянуть parser/knowledge traits до visual layer
Сделать так, чтобы style DB реально влияла на visual realization.

## Подэтап 9.6. Реализовать `GenerationMetadataRecorder`
Сохранять все generation traces.

## Подэтап 9.7. Добавить observability и тесты
Сделать Comfy pipeline измеримым и воспроизводимым.

---

# 24. Критерии готовности этапа

Этап 9 реализован корректно, если:

1. ComfyUI pipeline использует управляемые `visual presets`.
2. У разных режимов разные visual priorities:
   - `garment_matching` → anchor centrality high
   - `style_exploration` → diversity high
   - `occasion_outfit` → practical coherence high
3. Parser/knowledge-derived style data реально влияют на visual generation.
4. Anti-repeat constraints доходят не только до prompt, но и до visual pipeline.
5. Worker принимает structured `VisualGenerationPlan`, а не только prompt string.
6. Generation metadata сохраняется полно и пригодна для анализа.
7. Pipeline покрыт unit / integration / e2e тестами.
8. Новые presets и workflows добавляются без переписывания orchestrator.

---

# 25. Архитектурный итог этапа

После реализации Этапа 9 ComfyUI pipeline перестаёт быть “последним жёстким слоем” и становится полноценным управляемым visual generation layer:

- mode-aware;
- preset-aware;
- knowledge-aware;
- anti-repeat-aware;
- observability-friendly;
- готовым к очередям и воркерам;
- связанным с уже существующим parser/ingestion фундаментом.

Именно после такого Stage 9 project stack начинает работать как единая система:
- parser наполняет style DB;
- knowledge layer извлекает нужные cards;
- prompt builder формирует `FashionBrief`;
- visual generation layer управляемо превращает его в разнообразные и объяснимые изображения через ComfyUI.
