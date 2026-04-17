
# План переработки fashion chatbot  
## Обновлённый master-plan runtime architecture  
## С учётом:
- реализованного Этапа 1 (Product behavior and UX policy),
- Этапа 2 (Routing redesign),
- нового обязательного этапа `style_ingestion_semantic_distillation_plan_v2`,
- обновлённого Этапа 3 (Reasoning pipeline v2),
- обновлённого Этапа 4 (Profile context v2),
- обновлённого Этапа 5 (Knowledge layer expansion v2),
- обновлённого Этапа 6 (Voice and Persona layer v2),
- новых ограничений для не-админов,
- cooldown UX и обновлённого chat UI.

---

# 0. Назначение документа

Этот документ является **обновлённой полной версией** главного runtime master-plan проекта и должен рассматриваться как основной roadmap и архитектурная спецификация верхнего уровня для fashion chatbot после этапов 0–9.

Он фиксирует:

1. каким продуктом должен стать бот;
2. какие архитектурные принципы обязательны;
3. как теперь должен выглядеть runtime pipeline;
4. где в roadmap должен стоять parser upgrade;
5. как обновляются связи между:
   - routing,
   - parser,
   - reasoning,
   - profile context,
   - knowledge layer,
   - voice layer,
   - generation;
6. как должны быть встроены:
   - product behavior policy,
   - quotas/limits,
   - cooldown policy,
   - UI interaction rules.

Документ нужен для того, чтобы команда:
- не строила новые этапы на устаревших предпосылках;
- не делала двойную работу;
- сохраняла чистую архитектуру;
- могла масштабировать проект как серьёзную fashion AI систему, а не как набор частных хаков.

---

# 1. Контекст

## 1.1. Что уже есть после этапов 0–9

После уже реализованных этапов 0–9 проект стал заметно сильнее:
- есть style ingestion pipeline;
- есть база стилей;
- есть knowledge-oriented foundation;
- есть orchestrator;
- есть prompt builder;
- есть ComfyUI pipeline;
- есть generation jobs;
- есть частичное разделение reasoning и generation.

Это уже хороший фундамент.

---

## 1.2. Какие проблемы проявились после этого

Но в продукте стали видны системные проблемы:

1. бот слишком легко уходит в generation;
2. generation-oriented mode “залипает”;
3. свободный текст иногда продолжает visual flow, хотя не должен;
4. profile context не стал обязательной частью runtime;
5. knowledge layer ещё недостаточно зрелый;
6. parser слишком грубо режет style source text;
7. voice/persona ещё не оформлены как отдельный слой;
8. generation всё ещё рискует получать бедный или prose-засорённый input;
9. система пока недостаточно подготовлена к:
   - Malevich layer,
   - historian layer,
   - editorial stylist layer.

Следовательно, проект нужно перестроить не точечными правками, а как **единый runtime redesign**.

---

# 2. Новый продуктовый принцип

## 2.1. Что такое бот после redesign

Бот больше не должен быть:

> “чатом, который почти всегда рисует картинку”

Он должен стать:

> **fashion reasoning assistant**, который умеет:
- понять запрос;
- объяснить;
- подобрать;
- стилизовать;
- исторически и композиционно обосновать;
- говорить о цвете, свете, силуэте и ритме;
- визуализировать **только по осознанному триггеру**.

---

## 2.2. Базовая продуктовая формула

Продукт должен мыслиться как:

> **Fashion Reasoning System + Controlled Voice + Optional Visualization**

То есть:
- основа — reasoning;
- голос — отдельный слой;
- визуализация — не default, а optional branch.

---

## 2.3. Практический UX-принцип

Базовая UX-логика должна быть такой:

1. пользователь пишет сообщение;
2. бот по умолчанию отвечает **текстом** как умный стилист;
3. если визуализация уместна — она предлагается как отдельный следующий шаг;
4. генерация запускается только:
   - по кнопке `Попробовать другой стиль`,
   - по явному текстовому запросу пользователя,
   - после подтверждающего CTA.

Это уже было зафиксировано в Product behavior policy и остаётся фундаментом системы. 

---

# 3. Главный архитектурный принцип

## 3.1. Слои должны быть разделены

Новая архитектура должна строго разделять:

- **Routing** — определяет сценарий и generation intent
- **Retrieval** — собирает нужные данные
- **Parser / Semantic Distillation** — превращает source text в knowledge units
- **Profile Alignment** — персонализирует style knowledge
- **Reasoning** — решает, что посоветовать и какой brief собрать
- **Knowledge Layer** — поставляет typed knowledge bundles
- **Voice Layer** — решает, как сформулировать ответ
- **Generation** — строит визуализацию из structured brief
- **Product Policy / Access Control** — ограничивает usage, cooldown и interaction rules

---

## 3.2. Почему это критично

Если эти слои смешать:
- routing станет слишком тяжёлым;
- reasoner начнёт парсить и писать прозу одновременно;
- profile logic расползётся по prompt builder и frontend;
- voice начнёт придумывать fashion logic;
- generation будет получать prose вместо структуры;
- любые изменения будут вызывать каскадный refactor.

---

# 4. Полный новый runtime pipeline

## 4.1. Целевая схема

```text
User message
→ ProductPolicyGate
→ ConversationRouter
→ RoutingDecision

→ Retrieval profile selection
→ FashionReasoningContextAssembler
→ Knowledge Layer
→ ProfileContextService
→ ProfileStyleAlignmentService

→ FashionReasoner
→ FashionReasoningOutput

→ VoiceTonePolicy
→ VoiceLayerComposer
→ StyledAnswer

→ Optional CTA / optional generation branch
→ FashionBrief
→ Prompt Builder
→ ComfyUI
```

---

## 4.2. Что означает каждый шаг

### `ProductPolicyGate`
Проверяет:
- quotas;
- cooldown;
- access rules;
- можно ли вообще продолжать interaction.

### `ConversationRouter`
Semantic-first роутинг через vLLM:
- mode detection;
- generation intent;
- clarification need;
- continue/reset flow.

### `FashionReasoningContextAssembler`
Собирает:
- style bundles;
- `KnowledgeContext`;
- profile context;
- style history;
- diversity constraints;
- retrieval-specific data.

### `ProfileStyleAlignmentService`
Выравнивает style knowledge под конкретного пользователя.

### `FashionReasoner`
Принимает основное смысловое решение:
- что посоветовать;
- как это обосновать;
- нужен ли clarification;
- нужен ли CTA;
- какой `FashionBrief` собрать.

### `VoiceLayerComposer`
Формулирует ответ:
- стилистически;
- исторически;
- через controlled language of color/form when relevant.

### `Generation branch`
Запускается только при разрешённом product policy и явном visual trigger.

---

# 5. Новый порядок этапов roadmap

## 5.1. Старый порядок был уже недостаточен
Если идти по старому порядку без вставки parser upgrade:
- reasoning пришлось бы потом переписывать;
- knowledge layer пришлось бы переделывать;
- profile context не смог бы корректно работать с richer style signals;
- voice layer оказался бы построенным поверх бедного output.

---

## 5.2. Новый обязательный порядок

### Этап 1 — Product behavior and UX policy  
Уже реализован, но ниже зафиксированы новые patch-требования.

### Этап 2 — Routing redesign

### Этап 2.5 — Style ingestion semantic distillation  
**Новый обязательный этап**

### Этап 3 — Reasoning pipeline v2

### Этап 4 — Profile context v2

### Этап 5 — Knowledge layer expansion v2

### Этап 6 — Voice and Persona layer v2

---

## 5.3. Почему parser upgrade должен стоять после Этапа 2 и до Этапа 3

Потому что:
- router может строиться без глубокого parser enrichment;
- reasoning уже зависит от качества style data;
- profile alignment должен работать на richer style bundles;
- knowledge layer должен сразу строиться вокруг semantic-distilled style provider;
- voice layer должен опираться на enriched reasoning output.

Это решение уже было зафиксировано отдельно и здесь включается как обязательная часть master-plan. 

---

# 6. Этап 1 — Product behavior and UX policy (обновлённый статус)

## 6.1. Что уже зафиксировано и остаётся верным

- default mode = text-first
- generation only on explicit trigger
- no sticky generation mode
- after visual scenario → return to general advice
- only one quick visual button remains:
  - `Попробовать другой стиль`

Убираются сценарные кнопки:
- `Подобрать к вещи`
- `Что надеть на событие`

Они переводятся в natural language scenarios.

---

## 6.2. Что нужно добавить в Этап 1 как patch

### Новый блок 1. Role-based limits
Если user не админ:
- максимум 5 генераций в день
- максимум 10 минут текстового чата в день

### Новый блок 2. Cooldown UX
После:
- отправки сообщения
- нажатия `Попробовать другой стиль`

чат блокируется на 60 секунд.

### Новый блок 3. Rounded UI
Новый визуальный контракт:
- rounded chat shell
- rounded input
- rounded CTA
- rounded buttons
- calm minimal interface

### Новый блок 4. Circular loader
На месте кнопки отправки:
- чёрный фон
- белая круглая полоска
- 60-second progress / cooldown indicator

---

## 6.3. Почему это не часть parser
Эти изменения относятся к:
- product policy
- access control
- UI behavior
- runtime throttling

Они не должны смешиваться с parser upgrade.

---

# 7. Этап 2 — Routing redesign

## 7.1. Основной принцип
Основной mode detection делает не keyword if-chain, а:
- `ConversationRouter`
- через отдельный короткий vLLM call
- со strict JSON output

Keyword routing остаётся только fallback.

---

## 7.2. Что должен решать router
Router должен определять:
- mode
- confidence
- needs clarification
- missing slots
- generation intent
- continue existing flow
- reset to general
- reasoning depth
- retrieval profile hint

---

## 7.3. Обновлённый `RoutingDecision`

```python
class RoutingDecision:
    mode: str
    confidence: float
    needs_clarification: bool
    missing_slots: list[str]
    generation_intent: bool
    continue_existing_flow: bool
    should_reset_to_general: bool
    reasoning_depth: str
    retrieval_profile: str | None
```

---

## 7.4. Что router НЕ делает
- не делает retrieval
- не строит `FashionBrief`
- не читает parser tables
- не решает generation prompt
- не формулирует финальный ответ

---

## 7.5. Почему router должен остаться лёгким
Даже после parser upgrade router не должен тащить в себя:
- style facets;
- profile weighting logic;
- knowledge provider internals.

Он только открывает правильный downstream branch.

---

# 8. Этап 2.5 — Style ingestion semantic distillation

## 8.1. Почему это теперь ключевой обязательный этап
Раньше parser:
- слишком быстро схлопывал source text;
- терял visual language;
- терял styling rules;
- терял props;
- терял hierarchy;
- плохо годился и для generation, и для консультаций.

Теперь parser должен стать:
> **semantic knowledge production pipeline**

---

## 8.2. Новый принцип parser
Больше не:
```text
raw source text → coarse profile
```

А:
```text
raw source text
→ cleaning / sectioning
→ semantic distillation
→ structured JSON artifacts
→ normalized DB
→ runtime projections
```

---

## 8.3. Что parser теперь должен производить
На один стиль нужно уметь получать несколько typed JSON / semantic objects:

- `StyleCoreJson`
- `StyleKnowledgeJson`
- `StyleVisualLanguageJson`
- `StyleFashionItemsJson`
- `StyleImagePromptAtomsJson`
- `StyleRelationsJson`

---

## 8.4. Что это даёт downstream
### Для reasoning
- styling rules
- casual adaptations
- status markers
- overlap context
- history references

### Для generation
- hero garments
- props
- palette
- lighting
- photo treatment
- composition cues
- negative constraints

### Для knowledge layer
- typed knowledge projections
- cards/chunks/documents

---

## 8.5. Новый parser pipeline

```text
fetch raw source
→ normalize source
→ noise filtering
→ section classification
→ semantic distillation
→ advice facets
→ image facets
→ visual language facets
→ relations
→ persistence
→ runtime knowledge projection
```

---

## 8.6. Где parser входит в runtime indirectly
Parser не вызывается на каждый chat turn.  
Но его outputs now become foundational for:
- reasoning;
- profile alignment;
- knowledge provider;
- voice layer.

---

## 8.7. Backfill обязателен
Новый parser должен уметь:
- не только ingest new styles;
- но и reprocess already stored source texts.

Иначе runtime будет работать на смешанном качестве данных.

---

# 9. Этап 3 — Reasoning pipeline v2

## 9.1. Новый принцип reasoning
Reasoning работает:
- не на raw message only;
- не на parser source text;
- не только на coarse style summary;

а на:
- retrieved structured style knowledge;
- `KnowledgeContext`;
- profile-aware aligned style bundles;
- style history / anti-repeat signals.

---

## 9.2. Новый `FashionReasoningInput`

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

    style_context: list[StyleKnowledgeCard]
    style_advice_facets: list[StyleAdviceFacet]
    style_image_facets: list[StyleImageFacet]
    style_visual_language_facets: list[StyleVisualLanguageFacet]
    style_relation_facets: list[StyleRelationFacet]
    style_semantic_fragments: list[StyleSemanticFragmentSummary]
```

---

## 9.3. Новый `FashionReasoningOutput`

```python
class FashionReasoningOutput:
    response_type: str
    text_response: str
    clarification_question: str | None
    fashion_brief: FashionBrief | None
    can_offer_visualization: bool
    suggested_cta: str | None
    reasoning_metadata: ReasoningMetadata

    style_logic_points: list[str]
    visual_language_points: list[str]
    historical_note_candidates: list[str]
    styling_rule_candidates: list[str]
    image_cta_candidates: list[str]
```

---

## 9.4. Новый `FashionBrief`
Reasoning теперь обязан строить normalized brief из structured style facets:

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

    hero_garments: list[str]
    secondary_garments: list[str]
    visual_motifs: list[str]
    props: list[str]
    lighting_mood: list[str]
    photo_treatment: list[str]
```

---

## 9.5. Новый обязательный компонент
`FashionReasoningContextAssembler`

Он должен:
- собирать retrieval bundle;
- загружать style facets;
- поднимать profile context;
- собирать `KnowledgeContext`;
- подготавливать reasoner input.

---

## 9.6. Clarification-first policy
Reasoner должен уметь возвращать:
- clarification response
- без запуска generation
- без сырого `FashionBrief`, если данных пока недостаточно

---

# 10. Этап 4 — Profile context v2

## 10.1. Новый главный принцип
Profile context больше не применяется только в generation.  
Он должен применяться **до reasoning**.

---

## 10.2. Что такое profile context в новой системе
Это не “пол пользователя”, а presentation-oriented style profile:

- `presentation_profile`
- `fit_preferences`
- `silhouette_preferences`
- `comfort_preferences`
- `formality_preferences`
- `color_preferences`
- `color_avoidances`
- `preferred_items`
- `avoided_items`

---

## 10.3. Новый ключевой сервис
`ProfileStyleAlignmentService`

Он должен выравнивать:
- style advice facets
- style image facets
- visual language facets
- relation bundles

под конкретного пользователя.

---

## 10.4. Как profile участвует в runtime

```text
assembler
→ style facet bundle
→ profile alignment
→ profile-aligned bundle
→ reasoner
```

---

## 10.5. Что profile alignment делает
- filtering
- weighting
- boosting relevant options
- lowering conflicting signals
- casual/formality adaptation
- silhouette alignment

---

## 10.6. Что это даёт
- более персонализированные советы
- более точный `FashionBrief`
- меньше усреднённости
- меньше конфликта между text advice и generation

---

# 11. Этап 5 — Knowledge layer expansion v2

## 11.1. Новый главный принцип
Reasoning работает не с БД, а с:
> **Knowledge Providers**

---

## 11.2. Первый canonical provider
После parser upgrade `style_ingestion` provider должен стать:
> **semantic-distilled style provider**

а не thin wrapper над `style_profiles`.

---

## 11.3. Новые основные сущности

- `knowledge_providers`
- `knowledge_documents`
- `knowledge_chunks`
- `knowledge_cards`
- `knowledge_settings`

---

## 11.4. Новый `KnowledgeContext`

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

## 11.5. Новый style provider
`StyleDistilledKnowledgeProvider`

Он должен:
- читать semantic-distilled style outputs;
- проецировать их в knowledge units;
- отдавать runtime-friendly cards.

---

## 11.6. Почему knowledge layer теперь центральный
Он связывает:
- parser
- reasoning
- profile alignment
- future historian / stylist / Malevich providers
- voice layer

---

## 11.7. Graceful degradation обязателен
Если future providers пусты или выключены:
- runtime не ломается;
- style provider alone still works;
- product остаётся работоспособным.

---

# 12. Этап 6 — Voice and Persona layer v2

## 12.1. Новый главный принцип
Voice layer не генерирует смысл.  
Он формулирует уже полученный смысл.

---

## 12.2. Новый pipeline layer
```text
FashionReasoningOutput
→ VoiceTonePolicy
→ VoiceLayerComposer
→ StyledAnswer
```

---

## 12.3. Три слоя persona

### Базовый слой
Современный умный стилист  
(активен почти всегда)

### Исторический слой
Контекстный историк моды  
(подключается не всегда)

### Поэтика цвета и формы
Controlled language of light / plane / rhythm / contrast  
(подключается только when relevant)

---

## 12.4. Новый `VoiceContext`

```python
class VoiceContext:
    mode: str
    response_type: str
    desired_depth: str
    should_be_brief: bool
    can_use_historical_layer: bool
    can_use_color_poetics: bool
    can_offer_visual_cta: bool
    profile_context_present: bool
    knowledge_density: str
```

---

## 12.5. Новый `StyledAnswer`

```python
class StyledAnswer:
    text: str
    tone_profile: str
    voice_layers_used: list[str]
    includes_historical_note: bool
    includes_color_poetics: bool
    cta_text: str | None
    brevity_level: str
```

---

## 12.6. Что voice layer НЕ делает
- не меняет garments
- не меняет palette
- не меняет brief
- не пишет visual prompt
- не ходит в parser tables
- не invents new fashion logic

---

# 13. Access control, quotas и cooldown policy

## 13.1. Почему это отдельный слой
Quotas, limits и cooldown не относятся к parser, reasoning или voice.  
Это:
- product policy
- runtime governance
- resource protection
- UX control

---

## 13.2. Новое правило для не-админа

Если user не admin:
- не более 5 генераций в день
- не более 10 минут текстового чата в день

---

## 13.3. Новый сервис
`UsageAccessPolicyService`

```python
class UsageAccessPolicyService:
    async def evaluate(
        self,
        subject: UserContext,
        action: RequestedAction
    ) -> UsageDecision:
        ...
```

---

## 13.4. Доменные сущности

```python
class UsageQuota:
    daily_generation_limit: int
    daily_chat_seconds_limit: int

class UsageDecision:
    is_allowed: bool
    denial_reason: str | None
    remaining_generations: int
    remaining_chat_seconds: int
```

---

## 13.5. Где policy должна срабатывать
До:
- router
- reasoning
- generation
- Comfy job creation

То есть раньше дорогих вычислений.

---

# 14. Interaction cooldown policy

## 14.1. Что требуется
После:
- отправки сообщения
- нажатия `Попробовать другой стиль`

чат блокируется на 60 секунд.

---

## 14.2. Почему это не только UI feature
Frontend cooldown alone недостаточен, потому что его можно обойти через API.

Нужен:
- frontend visual cooldown
- backend throttle contract

---

## 14.3. Новый backend сервис
`InteractionThrottleService`

```python
class InteractionThrottleService:
    async def can_submit(
        self,
        user_id: str,
        action_type: str,
    ) -> ThrottleDecision:
        ...
```

---

## 14.4. Новый frontend UX contract
На месте кнопки отправки:
- круговой loader
- белая заполняющаяся линия
- чёрный фон
- 60-second progress state

То же правило действует после `Попробовать другой стиль`.

---

# 15. UI layer и новые interaction правила

## 15.1. Rounded UI contract
Новый визуальный контракт:
- все элементы чата rounded
- input rounded
- CTA rounded
- loader rounded
- мягкая визуальная подача
- clean minimal surface

---

## 15.2. Что это улучшает
- consistency
- perceived calmness
- product identity
- coherence with fashion-stylist positioning

---

## 15.3. FSD-friendly frontend blocks
Рекомендуемые блоки:
- `entities/usage-policy`
- `entities/chat-cooldown`
- `features/send-message`
- `features/style-exploration-trigger`
- `widgets/chat-panel`

---

# 16. Полная новая карта ключевых сервисов

## 16.1. Routing layer
- `RoutingContextBuilder`
- `ConversationRouter`
- `RoutingDecisionValidator`
- `FallbackRouterPolicy`

## 16.2. Parser / style ingestion layer
- `NoiseFilter`
- `SectionClassifier`
- `StyleSemanticDistillationService`
- `StyleFacetProjector`
- backfill services

## 16.3. Reasoning layer
- `FashionReasoningContextAssembler`
- `ProfileStyleAlignmentService`
- `FashionReasoner`
- `FashionBriefBuilder`

## 16.4. Profile layer
- `ProfileContextService`
- `ProfileContextNormalizer`
- `ProfileClarificationPolicy`
- `ProfileStyleAlignmentService`

## 16.5. Knowledge layer
- `StyleDistilledKnowledgeProvider`
- `KnowledgeProvidersRegistry`
- `KnowledgeContextAssembler`
- `KnowledgeCardRanker`

## 16.6. Voice layer
- `VoiceTonePolicy`
- `VoicePromptBuilder`
- `VoiceLayerComposer`

## 16.7. Generation layer
- `GenerationPolicyService`
- `PromptBuilder`
- `ComfyService`
- generation job orchestration

## 16.8. Product policy layer
- `UsageAccessPolicyService`
- `InteractionThrottleService`
- session / counters / role policies

---

# 17. Новые ключевые runtime contracts

## 17.1. `RoutingDecision`
Определяет scenario и downstream retrieval/reasoning profile.

## 17.2. `FashionReasoningInput`
Aggregates all runtime-relevant structured context.

## 17.3. `FashionReasoningOutput`
Разделяет:
- reasoning signals
- user text basis
- brief generation
- CTA eligibility

## 17.4. `FashionBrief`
Единый structured bridge between reasoning and generation.

## 17.5. `KnowledgeContext`
Unified runtime knowledge bundle.

## 17.6. `ProfileContextSnapshot`
Runtime-safe personal context.

## 17.7. `StyledAnswer`
Final voice-composed response.

---

# 18. Что должно быть строго запрещено

## 18.1. Нельзя
- смешивать routing и reasoning;
- смешивать parser и runtime reasoning;
- смешивать profile filtering и prompt building;
- смешивать knowledge и voice;
- пускать prose voice-layer output в visual prompt pipeline;
- делать frontend-only quotas/cooldowns;
- строить future providers как hardcoded if/else branches.

---

## 18.2. Почему
Это гарантирует:
- Clean Architecture
- OOP supportability
- scalable runtime
- predictable testing surface
- easier evolution

---

# 19. How the system scales

## 19.1. Почему архитектура теперь масштабируемая

Потому что:
- parser upgrade превращает source text в reusable knowledge
- providers делают retrieval extensible
- reasoner работает на typed bundles
- profile alignment изолирован
- voice layer изолирован
- generation изолирован
- policies вынесены отдельно

---

## 19.2. Что можно будет добавлять без слома
- новые style sources
- новые editorial providers
- новые persona layers
- новые profile fields
- новые generation models
- новые quotas/policies
- новые prompt builders
- новые routing modes

---

# 20. Clean Architecture / SOLID / OOP

## 20.1. SRP
Каждый слой делает одну понятную работу:
- Router → route
- Parser → distill
- Profile → align user context
- Knowledge → provide typed knowledge
- Reasoner → decide meaning
- Voice → formulate
- Generation → visualize
- Policy → enforce access/rate rules

---

## 20.2. OCP
Новые:
- providers
- persona layers
- profile fields
- style facets
- policies

добавляются расширением, а не переписыванием ядра.

---

## 20.3. DIP
Высокоуровневые слои зависят от:
- interfaces
- contracts
- bundles

а не от:
- ORM specifics
- parser SQL schema
- specific external clients

---

## 20.4. ООП-подход
Нужны:
- explicit domain objects
- explicit application services
- clear protocols/interfaces
- separate policy services
- immutable snapshots for runtime safety

---

# 21. Updated implementation roadmap

## Подэтап 1
Завершить patch к Этапу 1:
- limits
- cooldown
- rounded UI
- loader UX
- backend throttling

## Подэтап 2
Сделать Routing redesign

## Подэтап 2.5
Внедрить style ingestion semantic distillation:
- new ingestion
- backfill old source data
- compatibility projection

## Подэтап 3
Внедрить Reasoning pipeline v2:
- richer input
- brief builder
- clarification-first
- CTA candidates

## Подэтап 4
Внедрить Profile context v2:
- storage
- snapshot
- clarification policy
- profile alignment

## Подэтап 5
Внедрить Knowledge layer v2:
- providers
- style distilled provider
- cards/context
- flags
- graceful degradation

## Подэтап 6
Внедрить Voice & Persona layer v2:
- base stylist voice
- historian layer
- color/form poetics
- controlled CTA voice

## Подэтап 7
Интегрировать всё в orchestrator:
- policy gate
- router
- assembler
- aligner
- reasoner
- voice
- generation handoff

## Подэтап 8
Наблюдаемость и тесты:
- unit
- integration
- product tests
- tracing / logs / diagnostics

---

# 22. Acceptance criteria для master-plan

Система считается переработанной корректно, если:

1. Бот по умолчанию работает в text-first режиме.
2. Генерация запускается только по явному триггеру.
3. Sticky generation mode устранён.
4. Routing semantic-first и отделён от reasoning.
5. Parser upgraded до semantic distillation.
6. Parser outputs используются downstream, а не лежат мёртвым слоем.
7. Reasoning работает на structured style facets и `KnowledgeContext`.
8. Profile context применяется до reasoning, а не только в generation.
9. Knowledge layer provider-based и runtime-safe.
10. Voice layer отделён от reasoning и generation.
11. `FashionBrief` остаётся центральным bridge между reasoning и visual branch.
12. Voice prose не попадает в image prompt pipeline.
13. Для не-админа действуют:
    - 5 generations/day
    - 10 minutes chat/day
14. После send и after `Попробовать другой стиль` действует 60-second cooldown.
15. UI rounded и consistent.
16. Вся архитектура остаётся расширяемой и пригодной к поддержке.

---

# 23. Definition of Done для всего redesign

Runtime redesign можно считать успешно завершённым, если:

- бот перестал быть “обёрткой вокруг image generation”;
- бот стал реальным fashion reasoning assistant;
- parser, knowledge, profile, reasoning, voice и generation работают как связанные, но независимые слои;
- новые knowledge providers можно вводить без architectural chaos;
- продуктовая логика и usage governance оформлены отдельно;
- генерация стала более осознанной, а не автоматической;
- пользователь получает:
  - более умные советы,
  - более согласованные ответы,
  - более релевантную визуализацию,
  - более спокойный и предсказуемый UX.

---

# 24. Архитектурный итог

После реализации этого обновлённого master-plan система превращается из:

> “бота, который отвечает и часто рисует”

в:

> **архитектурно зрелую fashion intelligence platform**,  
> где:
> - parser превращает source text в typed knowledge,
> - knowledge layer управляет runtime retrieval,
> - profile layer делает ответ персонализированным,
> - reasoner строит смысл,
> - voice layer делает его целостным и человеческим,
> - generation остаётся controlled optional branch,
> - product policy удерживает UX, quota и resource discipline.

Именно это и есть целевая форма большого масштабируемого fashion chatbot проекта.
