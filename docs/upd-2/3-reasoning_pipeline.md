
# Этап 3. Reasoning pipeline  
## Обновлённый подробный план реализации reasoning pipeline для fashion chatbot  
## С учётом `style_ingestion_semantic_distillation_plan_v2`

## 0. Назначение документа

Этот документ обновляет Этап 3 roadmap и фиксирует, как должен быть реализован reasoning pipeline после того, как в roadmap добавлен отдельный этап `style_ingestion_semantic_distillation_plan_v2` между Routing redesign и Reasoning pipeline.

Цель обновления:
- не строить reasoning поверх старого coarse `style_profiles`;
- сразу спроектировать reasoning layer так, чтобы он использовал richer style knowledge;
- не делать повторный рефакторинг после внедрения semantic-distilled parser pipeline;
- обеспечить чистые контракты между routing, retrieval, reasoning, profile alignment, knowledge layer и generation.

Этот документ должен рассматриваться как новая версия Этапа 3 и заменяет старую трактовку reasoning pipeline, где style context в основном опирался на coarse style cards и summary-поля.

---

# 1. Контекст и причина обновления

## 1.1. Что изменилось в roadmap

После анализа roadmap было зафиксировано, что `style_ingestion_semantic_distillation_plan_v2` нужно ставить **после Этапа 2 (Routing redesign) и до Этапа 3 (Reasoning pipeline)**.

Это означает, что reasoning pipeline больше **не должен проектироваться вокруг старого coarse parser output**, а обязан сразу учитывать:

- semantic fragments;
- advice-oriented style facets;
- image-oriented style facets;
- richer visual language facets;
- расширенный provider-based knowledge layer.

---

## 1.2. Почему старой версии Этапа 3 уже недостаточно

Старая редакция Этапа 3 была хороша как архитектурный каркас, но после parser upgrade у неё появляется ограничение:

она предполагает, что reasoning опирается прежде всего на:
- `StyleKnowledgeCard`
- coarse `style_context`
- существующий `style_profiles` слой.

После `style_ingestion_semantic_distillation_plan_v2` это уже недостаточно, потому что richer style data живёт на более точном уровне:

- `style_knowledge_facets`
- `style_visual_facets`
- semantic fragments / runtime projections
- richer relations / prompt atoms / stylistic rules

Следовательно, reasoning pipeline нужно переписать так, чтобы он:
- не был привязан к legacy coarse style profile;
- умел работать с richer parser output;
- оставался совместимым с future knowledge providers;
- не тянул parser details в свои доменные контракты.

---

# 2. Цель этапа

После реализации обновлённого Этапа 3 система должна работать по такой схеме:

```text
RoutingDecision
→ Retrieval profile selection
→ FashionReasoningContextAssembler
→ FashionReasoningInput
→ FashionReasoner
→ FashionReasoningOutput
→ VoiceLayerComposer
→ text response / clarification / CTA / FashionBrief / generation handoff
```

Где:
- routing определяет сценарий;
- retrieval собирает нужный набор данных;
- reasoning делает fashion-domain осмысление;
- voice layer формулирует это пользователю;
- generation получает уже нормализованный `FashionBrief`.

---

# 3. Новый главный принцип reasoning pipeline

## 3.1. Reasoning должен работать не на raw text и не на coarse summary

Обновлённое правило:

> Reasoning pipeline обязан работать на **retrieved structured fashion knowledge**, а не на сырых source-текстах и не только на coarse style summary.

Это принципиально важно, потому что:
- raw source prose слишком шумный;
- coarse style summary теряет много полезной структуры;
- reasoning должен получать уже distilled knowledge, а не выполнять parser work повторно.

---

## 3.2. Что reasoning НЕ должен делать

Reasoner по-прежнему не должен:
- сам читать БД напрямую;
- сам выполнять parser extraction;
- сам делать retrieval;
- сам решать routing mode;
- сам вызывать ComfyUI;
- сам заниматься voice composition;
- сам управлять usage quotas;
- сам реализовывать cooldown policy.

Reasoner должен оставаться чистым application service, который работает на уже собранном domain input.

---

# 4. Обновлённая архитектурная роль reasoning pipeline

## 4.1. Reasoning pipeline — это мост между retrieval и generation

Reasoning pipeline должен:

1. интерпретировать пользовательский запрос;
2. сопоставлять его с retrieved style knowledge;
3. учитывать profile context;
4. учитывать diversity constraints и style history;
5. формировать осмысленный stylistic answer;
6. формировать `FashionBrief`;
7. решать, нужен ли:
   - text-only response,
   - clarification,
   - CTA,
   - visual-ready handoff.

---

## 4.2. Reasoning pipeline больше не должен быть “тонким prompt-wrapper”

Он должен стать отдельной доменной стадией, которая:
- оперирует typed contracts;
- использует clear input bundle;
- возвращает normalized output;
- легко тестируется;
- не зависит от конкретной модели и parser implementation.

---

# 5. Новый вход reasoning pipeline

## 5.1. Обновлённый `FashionReasoningInput`

Нужно заменить старую упрощённую модель на новую расширенную.

```python
class FashionReasoningInput:
    mode: str
    user_request: str
    recent_conversation_summary: str | None
    profile_context: ProfileContextSnapshot | None
    style_history: list[UsedStyleReference]
    diversity_constraints: DiversityConstraints | None
    active_slots: dict[str, str]
    knowledge_context: KnowledgeContext
    generation_intent: bool
    can_generate_now: bool
    retrieval_profile: str | None

    # Legacy-compatible style context
    style_context: list[StyleKnowledgeCard]

    # New richer style signals
    style_advice_facets: list[StyleAdviceFacet]
    style_image_facets: list[StyleImageFacet]
    style_visual_language_facets: list[StyleVisualLanguageFacet]
    style_relation_facets: list[StyleRelationFacet]

    # Optional distilled parser summaries
    style_semantic_fragments: list[StyleSemanticFragmentSummary]
```

---

## 5.2. Почему нужно несколько facet-бандлов

Разные части reasoning работают с разными типами style knowledge:

### `style_advice_facets`
Нужны для:
- стилистических правил;
- casual adaptations;
- layering logic;
- what-to-wear guidance;
- negative stylistic guidance.

### `style_image_facets`
Нужны для:
- hero garments;
- composition cues;
- props;
- generation preparation;
- CTA quality estimation.

### `style_visual_language_facets`
Нужны для:
- palette;
- lighting mood;
- photo treatment;
- visual motifs;
- platform-era visual logic.

### `style_relation_facets`
Нужны для:
- overlap context;
- historical references;
- related style expansion;
- anti-repeat diversification.

---

## 5.3. Почему нельзя ограничиться `style_context: list[StyleKnowledgeCard]`

Потому что тогда:
- `FashionReasoner` снова будет опираться на flattened knowledge;
- image logic и stylistic logic снова смешаются;
- часть parser upgrade окажется бесполезной;
- generation и advice будут конкурировать за один и тот же coarse input.

---

# 6. Новый retrieval stage перед reasoning

## 6.1. Retrieval profile selection

После `RoutingDecision` нужно явно определять, какой профиль retrieval нужен.

Пример:

- `light`
- `style_focused`
- `occasion_focused`
- `visual_heavy`

Это значение может приходить из router decision или рассчитываться orchestration layer.

---

## 6.2. Новый компонент: `FashionReasoningContextAssembler`

Это центральный новый сервис для Этапа 3.

```python
class FashionReasoningContextAssembler(Protocol):
    async def assemble(
        self,
        *,
        routing_decision: RoutingDecision,
        session_state: SessionStateSnapshot,
        profile_context: ProfileContextSnapshot | None,
        retrieval_profile: str | None,
    ) -> FashionReasoningInput:
        ...
```

---

## 6.3. Что обязан делать `FashionReasoningContextAssembler`

Он должен:
- читать relevant repositories;
- доставать style cards;
- доставать advice facets;
- доставать image facets;
- доставать visual language facets;
- доставать relation facets;
- доставать profile context;
- доставать style history;
- строить diversity constraints;
- собирать `KnowledgeContext`;
- отдавать готовый `FashionReasoningInput`.

---

## 6.4. Почему assembler обязателен

Если retrieval размазать:
- по orchestrator;
- по reasoner;
- по handlers;
- по prompt builder;

то reasoning pipeline быстро станет неуправляемым.

Assembler даёт:
- SRP;
- единый вход в reasoning;
- понятный debug point;
- возможность менять retrieval logic независимо от reasoner.

---

# 7. Обновлённый `KnowledgeContext`

## 7.1. `KnowledgeContext` должен стать richer

Теперь `KnowledgeContext` должен содержать не только generic cards, но и типизированные bundles.

```python
class KnowledgeContext:
    providers_used: list[str]
    knowledge_cards: list[KnowledgeCard]
    style_cards: list[StyleKnowledgeCard]
    style_advice_cards: list[KnowledgeCard]
    style_visual_cards: list[KnowledgeCard]
    style_history_cards: list[KnowledgeCard]
    editorial_cards: list[KnowledgeCard]
```

---

## 7.2. Почему это важно

Так:
- reasoner может различать типы знаний;
- voice layer позже может различать “что сказать” и “как сказать”;
- future providers (Malevich / historian / stylist) ложатся естественно;
- prompt builder не привязан к parser internals.

---

# 8. Новый `FashionReasoner`

## 8.1. Роль не меняется, но вход и ожидания меняются

`FashionReasoner` остаётся отдельным application service:

```python
class FashionReasoner(Protocol):
    async def reason(self, input: FashionReasoningInput) -> FashionReasoningOutput:
        ...
```

Но теперь он обязан:
- принимать richer structured input;
- осмыслять отдельно advice layer и visual layer;
- собирать `FashionBrief` из structured facts;
- не пытаться повторно извлекать parser semantics.

---

## 8.2. Новый внутренний принцип работы reasoner

Reasoner должен мыслить в три шага:

### Шаг 1. Interpret user need
- что именно хочет пользователь;
- нужен ли совет, образ, уточнение, визуализация;
- какова реальная stylistic задача.

### Шаг 2. Align with structured style knowledge
- какие style facets подходят;
- какие visual-language signals релевантны;
- какие styling rules применимы;
- какие profile preferences важны;
- какие anti-repeat ограничения надо учесть.

### Шаг 3. Produce two outputs at once
- user-facing reasoning result;
- normalized `FashionBrief` для downstream generation.

---

# 9. Обновлённый `FashionReasoningOutput`

## 9.1. Новый контракт

```python
class FashionReasoningOutput:
    response_type: str
    text_response: str
    clarification_question: str | None
    fashion_brief: FashionBrief | None
    can_offer_visualization: bool
    suggested_cta: str | None
    reasoning_metadata: ReasoningMetadata

    # NEW
    style_logic_points: list[str]
    visual_language_points: list[str]
    historical_note_candidates: list[str]
    styling_rule_candidates: list[str]
    image_cta_candidates: list[str]
```

---

## 9.2. Зачем нужны новые поля

Эти поля нужны не только для отладки.

Они позволяют:
- voice layer говорить богаче и точнее;
- CTA strategy понимать, уместна ли визуализация;
- future explainability/debug tools показывать, откуда появился ответ;
- не смешивать смысл reasoning с итоговым prose.

---

# 10. Обновлённый `FashionBrief`

## 10.1. Новый статус `FashionBrief`
`FashionBrief` остаётся центральным артефактом reasoning pipeline, но теперь должен строиться уже не из coarse style summary, а из structured style facets.

---

## 10.2. Обновлённый контракт

```python
class FashionBrief:
    intent: str
    style_direction: str | None
    garment_list: list[str]
    palette: list[str]
    silhouette: str | None
    materials: list[str]
    accessories: list[str]
    footwear: list[str]
    color_logic: str | None
    tailoring_logic: str | None
    historical_reference: str | None
    composition_rules: list[str]
    negative_constraints: list[str]

    # NEW
    hero_garments: list[str]
    secondary_garments: list[str]
    visual_motifs: list[str]
    props: list[str]
    lighting_mood: list[str]
    photo_treatment: list[str]
```

---

## 10.3. Откуда теперь берутся поля

### `garment_list`
Из:
- `style_advice_facets`
- `style_image_facets`

### `palette`
Из:
- `style_visual_language_facets`

### `composition_rules`
Из:
- `style_image_facets`
- visual-language cues
- reasoner synthesis

### `negative_constraints`
Из:
- advice facets
- image facets
- profile alignment filters

### `historical_reference`
Из:
- relation facets
- knowledge layer
- editorial providers

### `hero_garments`, `props`, `photo_treatment`
Из:
- `style_image_facets`
- `style_visual_language_facets`

---

# 11. Profile alignment inside reasoning

## 11.1. Почему profile alignment нельзя оставить только на prompt builder
Если применять profile context только на generation step:
- текстовые советы будут менее точными;
- reasoning будет думать “вообще”, а не для конкретного человека;
- `FashionBrief` получится слабее.

---

## 11.2. Новый helper: `ProfileStyleAlignmentService`

```python
class ProfileStyleAlignmentService(Protocol):
    async def align(
        self,
        profile: ProfileContextSnapshot,
        style_facets: StyleFacetBundle,
    ) -> ProfileAlignedStyleFacetBundle:
        ...
```

---

## 11.3. Что он должен делать
- отфильтровывать конфликтующие hero garments;
- усиливать fitting/silhouette-relevant сигналы;
- снижать вес неподходящих style advice;
- выбирать более релевантные casual / formal варианты;
- готовить aligned bundle для reasoning.

---

## 11.4. Где он включается
Между:
- `FashionReasoningContextAssembler`
- и `FashionReasoner`

То есть reasoner получает уже профильно выровненный bundle.

---

# 12. Diversity и anti-repeat в reasoning

## 12.1. Это не только generation concern
Если reasoning не знает о повторе:
- он будет советовать одно и то же;
- CTA и generation снова будут крутиться вокруг одинаковых решений;
- style exploration быстро станет скучным.

---

## 12.2. Что должен знать reasoning
В `FashionReasoningInput` нужно сохранять:
- previously used style clusters
- recently shown palettes
- recently used hero garments
- previously shown visual motifs

---

## 12.3. Что делать с этими данными
Reasoner должен:
- избегать однотипных решений;
- выбирать alternative but adjacent style directions;
- снижать вес повторяющихся image cues;
- формировать `FashionBrief` с лучшим разнообразием.

---

# 13. Clarification-first policy в reasoning

## 13.1. Reasoner должен уметь не только отвечать, но и останавливать поток
Если входных данных не хватает:
- по occasion
- по weather
- по silhouette preference
- по degree of visual intent

reasoner должен вернуть:
- `response_type = clarification`
- `clarification_question`
- `fashion_brief = None`

---

## 13.2. Что важно
Clarification не должен инициировать generation и не должен порождать “сырой визуальный brief”.

---

# 14. CTA logic после reasoning

## 14.1. CTA — не обязанность reasoner, но reasoner должен её готовить
Reasoner должен вернуть:
- `can_offer_visualization`
- `suggested_cta`
- `image_cta_candidates`

---

## 14.2. На чём должно основываться решение
CTA более уместна, если:
- есть достаточно сильный image facet bundle;
- visual language хорошо определён;
- `FashionBrief` построен уверенно;
- generation intent либо уже есть, либо естественно вытекает из ответа.

CTA менее уместна, если:
- reasoning mostly advisory;
- style data бедная;
- profile signals недостаточны;
- clarification всё ещё нужна.

---

# 15. Интеграция с voice layer

## 15.1. Reasoning output должен быть удобен для VoiceLayerComposer
После обновления Этапа 3 voice layer не должен достраивать fashion logic “из воздуха”.

Он должен получать:
- `text_response` как черновой смысл;
- `style_logic_points`
- `visual_language_points`
- `historical_note_candidates`
- `styling_rule_candidates`

И уже красиво формулировать финальный пользовательский текст.

---

## 15.2. Почему это важно
Так:
- reasoning отвечает за смысл;
- voice отвечает за подачу;
- knowledge и presentation не смешиваются;
- runtime contracts остаются чистыми.

---

# 16. Интеграция с knowledge layer

## 16.1. Reasoning pipeline должен ожидать semantic-distilled `style_ingestion` provider
После обновлённого parser pipeline `style_ingestion` provider больше не должен выглядеть как thin wrapper over `style_profiles`.

Он должен поставлять:
- runtime style cards;
- advice-oriented cards;
- visual language cards;
- image composition cards;
- relation and historical context cards.

---

## 16.2. Что это меняет для reasoning
`FashionReasoningContextAssembler` должен быть совместим с provider-based retrieval и не зависеть от конкретной схемы parser DB.

То есть reasoning должен зависеть от:
- `StyleFacetBundle`
- `KnowledgeContext`
- `StyleKnowledgeCard`

а не от конкретных SQL таблиц.

---

# 17. Новые доменные сущности

Ниже — минимальный список новых/обновлённых сущностей.

### `StyleAdviceFacet`
```python
class StyleAdviceFacet:
    style_id: int
    core_style_logic: list[str]
    styling_rules: list[str]
    casual_adaptations: list[str]
    statement_pieces: list[str]
    status_markers: list[str]
    overlap_context: list[str]
    historical_notes: list[str]
    negative_guidance: list[str]
```

### `StyleImageFacet`
```python
class StyleImageFacet:
    style_id: int
    hero_garments: list[str]
    secondary_garments: list[str]
    core_accessories: list[str]
    props: list[str]
    composition_cues: list[str]
    negative_constraints: list[str]
```

### `StyleVisualLanguageFacet`
```python
class StyleVisualLanguageFacet:
    style_id: int
    palette: list[str]
    lighting_mood: list[str]
    photo_treatment: list[str]
    mood_keywords: list[str]
    visual_motifs: list[str]
    platform_visual_cues: list[str]
```

### `StyleRelationFacet`
```python
class StyleRelationFacet:
    style_id: int
    related_styles: list[str]
    overlap_styles: list[str]
    historical_relations: list[str]
    brands: list[str]
    platforms: list[str]
```

### `StyleFacetBundle`
```python
class StyleFacetBundle:
    advice_facets: list[StyleAdviceFacet]
    image_facets: list[StyleImageFacet]
    visual_language_facets: list[StyleVisualLanguageFacet]
    relation_facets: list[StyleRelationFacet]
```

---

# 18. Application services

## 18.1. Основные сервисы обновлённого Этапа 3

### `FashionReasoningContextAssembler`
Собирает полный `FashionReasoningInput`

### `ProfileStyleAlignmentService`
Выравнивает style facets под profile context

### `FashionReasoner`
Делает смысловое fashion reasoning

### `FashionBriefBuilder`
Можно выделить отдельно, если нужно разгрузить reasoner

```python
class FashionBriefBuilder(Protocol):
    async def build(
        self,
        reasoning_state: IntermediateReasoningState
    ) -> FashionBrief:
        ...
```

---

## 18.2. Почему `FashionBriefBuilder` лучше выделить
Это помогает:
- не превращать reasoner в God-object;
- отдельно тестировать brief generation;
- переиспользовать brief logic в разных сценариях;
- легче развивать generation handoff.

---

# 19. Clean Architecture / SOLID

## 19.1. Domain layer
- `FashionReasoningInput`
- `FashionReasoningOutput`
- `FashionBrief`
- `StyleAdviceFacet`
- `StyleImageFacet`
- `StyleVisualLanguageFacet`
- `StyleRelationFacet`
- `StyleFacetBundle`

## 19.2. Application layer
- `FashionReasoningContextAssembler`
- `ProfileStyleAlignmentService`
- `FashionReasoner`
- `FashionBriefBuilder`

## 19.3. Infrastructure layer
- repositories / provider adapters for distilled style facets
- retrieval adapters
- reasoner client
- metrics/logging

## 19.4. Interface layer
- orchestrator adapters
- chat response mappers
- CTA response shaping
- generation handoff DTOs

---

## 19.5. SOLID акценты

### SRP
- retrieval отдельно
- profile alignment отдельно
- reasoning отдельно
- brief building отдельно
- voice composition отдельно

### OCP
Новые facet types и future knowledge providers должны добавляться расширением, а не переписыванием core reasoner.

### DIP
Reasoner зависит от contracts и bundles, а не от parser tables и не от SQL details.

---

# 20. Наблюдаемость

## 20.1. Что логировать

Для каждого reasoning run:
- routing mode
- retrieval profile
- used providers
- style facets count
- profile alignment applied / not applied
- clarification required / not required
- fashion brief built / not built
- CTA offered / not offered
- generation-ready / not ready

---

## 20.2. Почему это важно
Без этого нельзя понять:
- почему reasoning вышел слабым;
- почему CTA была/не была показана;
- почему brief не собрался;
- почему был повтор.

---

# 21. Тестирование

## 21.1. Unit tests
Нужны на:
- `FashionReasoningContextAssembler`
- `ProfileStyleAlignmentService`
- `FashionBriefBuilder`
- `FashionReasoner` output mapping

## 21.2. Integration tests
Нужны сценарии:
- style-focused advice
- occasion outfit advice
- clarification required
- visual offer
- generation-ready brief
- anti-repeat reroute

## 21.3. Regression tests
Обязательно на:
- старые запросы без parser v2 regression
- новые запросы на richer facets
- consistency between text response and FashionBrief

---

# 22. Пошаговый план реализации

## Подэтап 1. Обновить контракты
- `FashionReasoningInput`
- `FashionReasoningOutput`
- `FashionBrief`
- facet bundle модели

## Подэтап 2. Реализовать retrieval assembler
- retrieval profile support
- facet bundle loading
- style history loading
- diversity constraints loading

## Подэтап 3. Реализовать profile alignment
- profile × style facet merge
- filtering / weighting

## Подэтап 4. Обновить reasoner
- richer inputs
- clarification policy
- CTA candidate generation
- structured reasoning outputs

## Подэтап 5. Выделить `FashionBriefBuilder`
- normalized brief generation
- test coverage

## Подэтап 6. Подключить к orchestration
- router → assembler → aligner → reasoner → brief → voice/generation

## Подэтап 7. Добавить observability и regression tests
- logging
- compare outputs
- anti-repeat checks

---

# 23. Acceptance criteria

Этап считается завершённым, если:

1. Reasoning pipeline реализован уже с учётом semantic-distilled parser output.
2. `FashionReasoningInput` поддерживает richer style facets.
3. Retrieval вынесен в отдельный `FashionReasoningContextAssembler`.
4. Появился `ProfileStyleAlignmentService`.
5. `FashionBrief` строится из advice/image/visual language facets.
6. Reasoner возвращает не только текст, но и structured reasoning signals.
7. CTA на визуализацию зависит от качества style/image context.
8. Reasoning не зависит напрямую от parser SQL schema.
9. Voice layer может формулировать enriched reasoning output без повторного построения fashion logic.
10. Generation handoff получает richer normalized brief.

---

# 24. Definition of Done

Этап считается реализованным корректно, если:
- reasoning больше не опирается только на coarse `style_profiles`;
- parser upgrade реально используется downstream;
- нет необходимости переписывать reasoning после подключения richer style provider в knowledge layer;
- `FashionBrief` и user-facing response остаются согласованными;
- архитектура остаётся чистой, расширяемой и пригодной для большого масштабируемого проекта.
