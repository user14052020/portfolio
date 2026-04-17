
# Этап 5. Knowledge Layer Expansion  
## Обновлённый подробный план реализации расширяемого knowledge layer для fashion chatbot  
## С учётом `style_ingestion_semantic_distillation_plan_v2`, обновлённого Этапа 3 (Reasoning pipeline) и обновлённого Этапа 4 (Profile Context)

## 0. Назначение документа

Этот документ является **полноценной обновлённой версией Этапа 5** и заменяет прежнюю редакцию `5-knowledge_layer_expansion.md` в рамках нового roadmap, где между Routing redesign и Reasoning pipeline уже добавлен отдельный этап `style_ingestion_semantic_distillation_plan_v2`.

Цель обновления:

- не строить knowledge layer вокруг старого coarse `style_profiles` как единственного источника style knowledge;
- сразу заложить knowledge layer так, чтобы первым canonical provider стал **semantic-distilled style provider**;
- связать parser upgrade с runtime retrieval, reasoning, profile alignment и future persona/voice expansion;
- не делать повторный рефакторинг knowledge architecture после подключения richer parser output;
- сохранить чистую архитектуру, provider-based abstraction, расширяемость и пригодность к поддержке на больших проектах.

После parser upgrade и обновлённого Этапа 3 knowledge layer больше не может трактоваться как “общая прослойка над style DB”. Он должен стать **typed, provider-oriented, runtime-safe knowledge fabric**, которая:
- уже сейчас обслуживает reasoning на базе стилей;
- позже без архитектурного слома подключает:
  - Малевича,
  - историка моды,
  - стилиста,
  - future editorial knowledge sources.

---

# 1. Контекст и причина обновления

## 1.1. Что изменилось после вставки parser upgrade

Раньше knowledge layer можно было проектировать так:
- есть style ingestion pipeline;
- есть style DB;
- styles являются основным источником;
- knowledge cards можно строить из coarse `style_profiles`, `style_traits`, `style_relations`.

Но после появления `style_ingestion_semantic_distillation_plan_v2` style ingestion radically усилился:
- source text перестаёт схлопываться слишком рано;
- появляются semantic fragments;
- появляются advice-oriented facets;
- появляются image-oriented facets;
- появляются richer visual language projections;
- style relations становятся богаче;
- style source превращается не просто в catalog entity, а в набор reusable knowledge objects.

Это означает, что knowledge layer нужно перестроить так, чтобы `style_ingestion` provider отдавал уже **distilled style knowledge**, а не thin wrapper over legacy style tables.

---

## 1.2. Почему старая версия Этапа 5 уже недостаточна

Исходный Этап 5 был концептуально сильным:
- provider-based knowledge architecture;
- `knowledge_providers`;
- `knowledge_documents`;
- `knowledge_chunks`;
- `knowledge_cards`;
- feature flags and graceful degradation;
- styles как первый canonical provider. 

Но он ещё не учитывал в полной мере, что после parser upgrade provider `style_ingestion` меняется по природе.

### Было
`style_ingestion` provider = coarse style DB source

### Должно стать
`style_ingestion` provider = **semantic-distilled style knowledge provider**

И это очень важная разница, потому что:
- reasoning pipeline v2 теперь ожидает richer style bundles;
- profile context v2 теперь выравнивает style facets до reasoning;
- voice/persona слой должен получать более точные knowledge-backed reasoning outputs;
- generation handoff больше не должен строиться на prose и бедных summary.

Следовательно, Этап 5 нужно обновить так, чтобы он:
- полноценно связал parser upgrade и runtime retrieval;
- стал “центральным знаниевым слоем”, а не просто общей таблицей текстов;
- не требовал позднего refactor, когда появятся editorial providers.

---

# 2. Цель этапа

После реализации обновлённого Этапа 5 система должна иметь knowledge layer, который:

1. Уже сейчас устойчиво работает на существующей style knowledge базе.
2. Использует parser-upgraded semantic-distilled style data как первый canonical provider.
3. Может без архитектурной ломки подключать:
   - Malevich / color-poetics layer,
   - fashion historian,
   - stylist / editorial rules,
   - future curated sources.
4. Поддерживает provider-based retrieval.
5. Поддерживает typed knowledge units, а не только raw text chunks.
6. Умеет gracefully деградировать, если provider выключен или таблицы пустые.
7. Даёт reasoning pipeline единый `KnowledgeContext`.
8. Не заставляет reasoner и voice layer работать напрямую с raw parser schema.
9. Сохраняет clean layering между:
   - ingestion,
   - storage,
   - retrieval,
   - reasoning,
   - presentation.

---

# 3. Главный архитектурный принцип knowledge layer

## 3.1. Knowledge layer — это не “таблица текстов”

Это базовое правило нужно сохранить и усилить.

Нельзя делать так:
- одна общая таблица knowledge_texts;
- туда складываются styles, Малевич, историк, стилист;
- reasoning “сам разберётся”.

Это приводит к:
- отсутствию типизации;
- плохому retrieval quality;
- плохой explainability;
- слабому runtime control;
- росту связности;
- размытию границ между knowledge, voice и reasoning.

---

## 3.2. Knowledge layer должен быть provider-oriented и typed

То есть знание организуется как сочетание:

```text
provider
→ document
→ chunk
→ card
→ runtime context
```

Но после parser upgrade к этому нужно добавить ещё один уровень осмысления:

```text
source text
→ semantic distillation
→ style facets / semantic projections
→ knowledge documents / chunks / cards
→ runtime retrieval
```

Следовательно, knowledge layer должен уметь работать не только с raw document model, но и с **knowledge projections**, построенными из distilled parser outputs.

---

## 3.3. Новое уточнение
Теперь базовый принцип звучит так:

> **Knowledge layer — это typed runtime abstraction над domain knowledge, а не над сырыми таблицами и не над parser internals.**

---

# 4. Базовая роль knowledge layer в обновлённой системе

## 4.1. Что было раньше
Knowledge layer мог казаться “будущей инфраструктурой под Malevich / historian / stylist”, а style DB — отдельно живущей системой.

## 4.2. Что должно быть теперь
Knowledge layer должен стать **обязательной runtime-прослойкой** уже для текущего style reasoning.

То есть:
- parser distills source text;
- style provider превращает distilled outputs в knowledge units;
- reasoning читает не parser tables, а `KnowledgeContext`;
- profile layer выравнивает style facet bundles;
- voice layer формулирует enriched reasoning output.

---

## 4.3. Практическая схема

```text
style source text
→ parser semantic distillation
→ style facets
→ style distilled provider
→ knowledge cards / context
→ reasoning
→ voice
→ generation handoff
```

Это и есть новая knowledge-centric архитектура runtime.

---

# 5. Что такое provider в обновлённой архитектуре

## 5.1. Provider — это источник domain knowledge, а не таблица

Примеры providers:
- `style_ingestion`
- `malevich`
- `fashion_historian`
- `stylist_editorial`

Provider определяет:
- происхождение знания;
- его тип;
- его runtime роль;
- его приоритет;
- его включённость в ingestion / runtime;
- правила retrieval участия.

---

## 5.2. Почему provider abstraction теперь ещё важнее
После parser upgrade нельзя вшивать style knowledge напрямую в reasoner, потому что:
- facets будут развиваться;
- появятся новые parser versions;
- появятся новые editorial providers;
- часть runtime может переключаться между providers через feature flags.

Provider abstraction позволяет:
- не вшивать special-case logic;
- не ломать OCP;
- делать feature-flag rollout;
- сравнивать provider quality;
- безопасно отключать новые sources.

---

# 6. `style_ingestion` как первый canonical provider

## 6.1. Главная новая фиксация этапа

После parser upgrade `style_ingestion` provider должен стать **semantic-distilled provider**, а не legacy adapter поверх old style tables.

---

## 6.2. Что это значит practically
Этот provider должен читать уже не только:
- `styles`
- `style_profiles`
- `style_traits`

а ещё и:
- `style_semantic_fragments`
- `style_knowledge_facets`
- `style_visual_facets`
- richer relation data
- compatibility projections

И превращать их в typed runtime knowledge units.

---

## 6.3. Почему это критично
Если этого не сделать:
- parser upgrade не будет использоваться downstream полноценно;
- reasoning pipeline v2 снова окажется на flattened data;
- knowledge layer останется формально красивой, но реально бедной;
- потом придётся заново переписывать style provider.

---

# 7. Новая knowledge taxonomy

## 7.1. Зачем нужна расширенная taxonomy
Reasoning и voice layer не должны видеть “просто текст”.

Они должны понимать, с каким типом знания работают:
- stylistic rule,
- visual language,
- history,
- composition pattern,
- prop logic,
- color theory,
- editorial note,
- prompt pattern.

---

## 7.2. Базовые knowledge types из предыдущего плана
Нужно сохранить:
- `style_catalog`
- `style_description`
- `style_composition`
- `color_theory`
- `composition_theory`
- `light_theory`
- `fashion_history`
- `style_history`
- `styling_rules`
- `tailoring_principles`
- `materials_fabrics`
- `occasion_rules`
- `flatlay_prompt_patterns`

---

## 7.3. Что обязательно добавить после parser upgrade
Теперь taxonomy нужно расширить новыми style-oriented knowledge types:

- `style_visual_language`
- `style_image_composition`
- `style_props`
- `style_signature_details`
- `style_styling_rules`
- `style_casual_adaptations`
- `style_negative_guidance`
- `style_relation_context`
- `style_brands_platforms`
- `style_palette_logic`
- `style_photo_treatment`

---

## 7.4. Почему это важно
Именно эти типы позволят:
- retrieval вытаскивать advice и image-knowledge отдельно;
- reasoner не смешивать styling advice и visual composition;
- generation handoff собирать richer briefs;
- voice layer красиво объяснять уже типизированные смысловые блоки.

---

# 8. Новые таблицы knowledge layer

## 8.1. `knowledge_providers`

### Назначение
Реестр источников знаний.

### Базовые поля
- `id`
- `code`
- `name`
- `provider_type`
- `description`
- `is_enabled`
- `is_runtime_enabled`
- `is_ingestion_enabled`
- `priority`
- `created_at`
- `updated_at`

### Примеры кодов
- `style_ingestion`
- `malevich`
- `fashion_historian`
- `stylist_editorial`

---

## 8.2. `knowledge_documents`

### Назначение
Хранит документы и документоподобные знания как source units.

### Поля
- `id`
- `provider_id`
- `title`
- `author`
- `source_ref`
- `language`
- `raw_text`
- `clean_text`
- `version`
- `is_active`
- `created_at`
- `updated_at`

---

## 8.3. `knowledge_chunks`

### Назначение
Хранит semantic fragments документов, пригодные для retrieval.

### Поля
- `id`
- `document_id`
- `chunk_index`
- `knowledge_type`
- `chunk_text`
- `summary`
- `tags_json`
- `metadata_json`
- `created_at`

---

## 8.4. `knowledge_cards`

### Назначение
Главная runtime-таблица нормализованных knowledge units.

### Поля
- `id`
- `provider_id`
- `knowledge_type`
- `title`
- `summary`
- `body`
- `tone_role`
- `style_id` nullable
- `style_family` nullable
- `era_code` nullable
- `tags_json`
- `metadata_json`
- `confidence`
- `is_active`
- `created_at`
- `updated_at`

---

## 8.5. `knowledge_settings`

### Назначение
Feature flags и runtime settings.

### Поля
- `id`
- `key`
- `value_json`
- `updated_at`
- `updated_by`

### Ключи
- `knowledge.providers.style_ingestion.enabled`
- `knowledge.providers.malevich.enabled`
- `knowledge.providers.fashion_historian.enabled`
- `knowledge.providers.stylist.enabled`
- `knowledge.reasoning.enable_historical_layer`
- `knowledge.reasoning.enable_color_poetics`
- `knowledge.routing.use_editorial_sources`

---

# 9. Почему нужен уровень `knowledge_cards`

## 9.1. Нельзя reasoner'у отдавать raw documents
Если reasoner будет получать:
- длинные documents;
- сырые source sections;
- whole parser outputs;
- нерелевантные text chunks;

то:
- retrieval станет шумным;
- prompts станут тяжёлыми;
- output потеряет управляемость;
- reasoning начнёт заново делать parser work.

---

## 9.2. `knowledge_cards` — это runtime-ready abstraction
Они нужны для того, чтобы:
- сделать retrieval стабильным;
- дать uniform format разным providers;
- не заставлять reasoner знать source schema;
- упростить explainability;
- разгрузить runtime prompts.

---

## 9.3. Новый принцип после parser upgrade
Теперь knowledge cards должны строиться не только из raw documents/chunks, но и из **distilled style facet projections**.

То есть:
- parser upgrade → facets
- facets → cards
- cards → retrieval
- retrieval → reasoner

---

# 10. Новый provider: `StyleDistilledKnowledgeProvider`

## 10.1. Это ключевой новый adapter Этапа 5

```python
class StyleDistilledKnowledgeProvider(KnowledgeProvider):
    async def retrieve(self, query: KnowledgeQuery) -> list[KnowledgeCard]:
        ...
```

---

## 10.2. Что он должен читать

Он должен читать:
- `style_knowledge_facets`
- `style_visual_facets`
- `style_relations`
- semantic fragment summaries
- compatibility `styles` rows
- optional legacy `style_profiles` only as fallback

---

## 10.3. Что он должен отдавать

Он должен строить карточки вроде:
- `style_description`
- `style_styling_rules`
- `style_casual_adaptations`
- `style_visual_language`
- `style_image_composition`
- `style_props`
- `style_relation_context`
- `style_brands_platforms`
- `style_palette_logic`

---

## 10.4. Почему это лучше, чем читать parser tables напрямую
Так:
- runtime не привязан к SQL schema parser;
- можно менять parser version без ломки reasoner;
- provider остаётся единым стабильным входом;
- cards удобно кешировать, логировать и versioning-овать.

---

# 11. Новый document-chunk-card pipeline для style provider

## 11.1. Что нужно делать со style facets
Нужно formalize pipeline:

```text
style parser outputs
→ style facet records
→ style distilled documents
→ style distilled chunks
→ style knowledge cards
→ runtime retrieval
```

---

## 11.2. Почему нужен document/chunk слой, если уже есть facets
Потому что:
- future retrieval и indexing удобнее делать через chunk model;
- documents/chunks помогают explainability;
- knowledge cards остаются runtime-friendly final projection;
- можно переиспользовать pipeline для future editorial providers.

---

## 11.3. Где должен жить facet → card projection
Нужен отдельный сервис:

```python
class StyleFacetKnowledgeProjector(Protocol):
    async def project(self, style_id: int) -> StyleKnowledgeProjectionResult:
        ...
```

Он должен:
- читать facet bundle;
- строить semantic documents/chunks/cards;
- сохранять их в knowledge layer tables.

---

# 12. `KnowledgeProvidersRegistry`

## 12.1. Роль registry сохраняется, но становится важнее
Нужен реестр, который:
- знает все providers;
- знает, какие providers enabled;
- знает priority;
- умеет gracefully пропускать пустые providers;
- отдаёт enabled runtime providers reasoning pipeline.

```python
class KnowledgeProvidersRegistry(Protocol):
    async def get_enabled_runtime_providers(self) -> list[KnowledgeProvider]:
        ...
```

---

## 12.2. Почему registry теперь критичен
После parser upgrade появляются:
- richer style provider;
- future Malevich provider;
- future Historian provider;
- future Stylist provider.

Без registry orchestrator и reasoner очень быстро превратятся в if/else jungle.

---

# 13. Graceful degradation

## 13.1. Что должно работать уже сейчас
Если таблицы для:
- `malevich`
- `fashion_historian`
- `stylist_editorial`

пока пустые, runtime:
- не падает;
- не выбрасывает ошибку;
- не пытается фейково “додумать” отсутствие данных;
- продолжает работать на `style_ingestion`.

---

## 13.2. Реализация
Через registry и provider contract:

```python
enabled_providers = registry.get_enabled_runtime_providers()
cards = []
for provider in enabled_providers:
    cards.extend(await provider.retrieve(query))
```

Если provider:
- выключен;
- пуст;
- временно unavailable;

то:
- он возвращает пустой список;
- pipeline продолжается.

---

## 13.3. Почему это особенно важно после parser upgrade
Потому что rollout richer style provider тоже может быть постепенным:
- сначала partial styles;
- потом backfill;
- потом migration from legacy.

Система должна жить в mixed state безопасно.

---

# 14. `KnowledgeContext` как runtime contract

## 14.1. Новый richer `KnowledgeContext`

После обновлённого Этапа 3 `KnowledgeContext` должен содержать не просто cards, а структурированный knowledge bundle.

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

## 14.2. Почему это важно
Так:
- reasoner может различать типы знания;
- profile alignment легче сопоставлять faceted style knowledge;
- voice layer later получает richer structured hints;
- system остаётся future-extensible.

---

# 15. `KnowledgeQuery`

## 15.1. Нужно явно описать query model
Reasoning pipeline не должен просто говорить registry:
- “дай что-нибудь”.

Нужен нормализованный query contract:

```python
class KnowledgeQuery:
    mode: str
    user_request: str
    style_ids: list[int] | None
    style_families: list[str] | None
    eras: list[str] | None
    retrieval_profile: str | None
    need_visual_knowledge: bool
    need_historical_knowledge: bool
    need_styling_rules: bool
    need_color_poetics: bool
    limit: int
```

---

## 15.2. Почему это важно
Так registry и providers могут:
- отдавать более релевантные cards;
- не таскать лишние знания;
- поддерживать reasoning depth / retrieval_profile;
- позже подключать новых providers без смены orchestrator API.

---

# 16. Интеграция с parser upgrade

## 16.1. Где style semantic distillation пересекается с knowledge layer
После parser upgrade появляются:
- semantic fragments;
- advice facets;
- image facets;
- visual language facets;
- relation facets.

Эти данные не должны оставаться “внутри parser subsystem”.

Они должны стать:
- first-class provider source
- knowledge documents
- knowledge chunks
- knowledge cards

---

## 16.2. Новый промежуточный слой
Нужен явный projection layer:

```text
parser facets
→ style distilled projection
→ knowledge layer
```

---

## 16.3. Почему это предотвращает двойную работу
Если сразу построить knowledge layer вокруг distilled provider:
- reasoning pipeline v2 не придётся потом переделывать;
- profile alignment уже будет работать на стабильных bundles;
- voice layer later не придётся переподключать заново;
- future providers будут добавляться по тому же паттерну.

---

# 17. Интеграция с reasoning pipeline v2

## 17.1. Что должен видеть `FashionReasoningContextAssembler`
Assembler должен работать через knowledge provider layer и получать:
- `style_context`
- `style_advice_facets`
- `style_visual_language_facets`
- `style_image_facets`
- relation/history cards

---

## 17.2. Почему assembler не должен читать parser DB
Иначе:
- knowledge layer теряет смысл;
- reasoner становится привязан к ingestion schema;
- provider abstraction становится формальной;
- OCP ломается.

---

## 17.3. Новый принцип
Reasoning depends on:
- `KnowledgeContext`
- `StyleFacetBundle`
- `StyleKnowledgeCard`

Но не на:
- `style_semantic_fragments` table
- `style_visual_facets` SQL schema
- `style_knowledge_facets` ORM details

---

# 18. Интеграция с profile context v2

## 18.1. Profile layer не должен ходить напрямую в DB
Он должен работать с bundle, полученным из knowledge/provider layer.

---

## 18.2. Что это даёт
Profile alignment получает:
- clean runtime contracts;
- profile-relevant style facets;
- более понятный weighting surface.

---

## 18.3. Следствие
Knowledge layer становится не просто retrieval infrastructure, а **shared runtime knowledge contract** для:
- reasoning;
- profile alignment;
- voice layer;
- generation handoff.

---

# 19. Интеграция с voice/persona layer

## 19.1. Voice layer не должен invent new logic
Он должен работать на enriched reasoning output, а enriched reasoning output строится на knowledge layer.

---

## 19.2. Что это значит для knowledge layer
Нужно уметь поставлять в reasoning:
- исторические note candidates;
- stylistic rule candidates;
- visual language candidates;
- color-poetic or composition theory snippets;
- editorial context cards.

---

## 19.3. Почему это важно
Именно knowledge layer позволяет:
- не смешивать knowledge и voice;
- делать persona layers управляемыми;
- не тащить длинные source texts в финальные prompts.

---

# 20. Admin flags и управление провайдерами

## 20.1. Что должно быть доступно из админки
Админка должна позволять:
- включать/выключать provider;
- регулировать provider priority;
- включать/выключать отдельные reasoning layers;
- тестировать new providers safely.

---

## 20.2. Минимальные флаги
- `style_ingestion_enabled`
- `malevich_enabled`
- `fashion_historian_enabled`
- `stylist_enabled`
- `use_editorial_knowledge`
- `use_historical_context`
- `use_color_poetics`

---

## 20.3. Где применяются
Флаги должны читаться:
- в `KnowledgeProvidersRegistry`
- в `FashionReasoningContextAssembler`
- в `FashionReasoner`
- в `VoiceLayerComposer`

---

# 21. Новые application services

## 21.1. `StyleFacetKnowledgeProjector`
Строит documents/chunks/cards из parser facets.

## 21.2. `KnowledgeProvidersRegistry`
Управляет providers.

## 21.3. `KnowledgeContextAssembler`
Можно выделить отдельно, если нужно разгрузить reasoning assembler.

```python
class KnowledgeContextAssembler(Protocol):
    async def assemble(self, query: KnowledgeQuery) -> KnowledgeContext:
        ...
```

## 21.4. `KnowledgeCardRanker`
Опциональный сервис, если retrieval logic станет сложнее:

```python
class KnowledgeCardRanker(Protocol):
    async def rank(
        self,
        query: KnowledgeQuery,
        cards: list[KnowledgeCard],
    ) -> list[KnowledgeCard]:
        ...
```

---

# 22. Почему `KnowledgeCardRanker` может понадобиться
После parser upgrade cards станут разнообразнее:
- advice cards;
- visual cards;
- historical cards;
- relation cards.

Reasoner не должен получать всё подряд в random order.  
Нужен ranking по relevance / diversity / priority.

---

# 23. Observability

## 23.1. Что логировать
Для каждого retrieval run:
- query mode
- retrieval profile
- providers used
- cards returned per provider
- cards filtered out
- style provider projection version
- empty providers
- provider latency
- ranking decisions

---

## 23.2. Что логировать для style provider
- number of cards projected from facets
- knowledge types emitted
- styles with low richness
- fallback to legacy summary if any
- parser version used for projection

---

## 23.3. Почему это важно
Без этого нельзя понять:
- почему reasoner получил бедный context;
- почему provider почти ничего не вернул;
- где knowledge layer шумит;
- где parser upgrade не дал ожидаемого runtime эффекта.

---

# 24. Тестирование

## 24.1. Unit tests
Нужны на:
- `StyleFacetKnowledgeProjector`
- `KnowledgeProvidersRegistry`
- `KnowledgeContextAssembler`
- `KnowledgeCardRanker`
- provider adapters

---

## 24.2. Integration tests
Нужны сценарии:
- style provider only
- style provider + empty editorial providers
- style provider + future historian provider
- parser facets → cards → reasoning retrieval
- feature flags on/off
- graceful degradation

---

## 24.3. Product tests
Нужно проверять:
- reasoner действительно стал богаче;
- visual CTA стала релевантнее;
- historical / editorial layers включаются только когда надо;
- отсутствие provider не ломает runtime.

---

# 25. Clean Architecture / SOLID

## 25.1. Domain layer
- `KnowledgeQuery`
- `KnowledgeCard`
- `KnowledgeContext`
- `KnowledgeProviderConfig`

## 25.2. Application layer
- `StyleFacetKnowledgeProjector`
- `KnowledgeProvidersRegistry`
- `KnowledgeContextAssembler`
- `KnowledgeCardRanker`

## 25.3. Infrastructure layer
- repositories for `knowledge_*`
- provider adapters
- projector persistence adapters
- admin settings repository

## 25.4. Interface layer
- admin endpoints
- diagnostics endpoints
- retrieval debug DTOs

---

## 25.5. SOLID акценты

### SRP
- provider fetch отдельно;
- facet projection отдельно;
- context assembly отдельно;
- ranking отдельно.

### OCP
Новые providers добавляются расширением, а не переписыванием registry/reasoner.

### DIP
Reasoner и voice layer зависят от `KnowledgeContext` и provider interfaces, а не от DB schema.

---

# 26. Пошаговый план реализации

## Подэтап 1. Обновить knowledge contracts
- `KnowledgeQuery`
- `KnowledgeContext`
- `KnowledgeCard`
- provider interfaces

## Подэтап 2. Реализовать `StyleFacetKnowledgeProjector`
- facets → documents/chunks/cards
- persistence
- version support

## Подэтап 3. Реализовать `StyleDistilledKnowledgeProvider`
- runtime retrieval from distilled style knowledge
- fallback compatibility

## Подэтап 4. Обновить `KnowledgeProvidersRegistry`
- style provider as first canonical provider
- feature flags
- graceful degradation

## Подэтап 5. Реализовать `KnowledgeContextAssembler`
- multi-provider retrieval
- typed context shaping
- retrieval_profile support

## Подэтап 6. Опционально добавить `KnowledgeCardRanker`
- relevance
- diversity
- provider priority

## Подэтап 7. Интегрировать с reasoning/profile/voice
- reasoning assembler
- profile alignment
- voice hints

## Подэтап 8. Добавить observability и tests
- logs
- metrics
- integration tests
- product tests

---

# 27. Acceptance criteria

Этап считается завершённым, если:

1. Knowledge layer больше не строится вокруг coarse style profile only.
2. `style_ingestion` provider работает как semantic-distilled provider.
3. Parser-upgraded style facets проецируются в knowledge documents/chunks/cards.
4. Reasoning pipeline получает `KnowledgeContext`, а не читает parser DB напрямую.
5. Profile alignment работает с runtime knowledge bundles, а не с raw tables.
6. Graceful degradation работает при пустых editorial providers.
7. Feature flags позволяют включать/выключать providers без деплоя.
8. New knowledge types покрывают visual language, styling rules, props, relations и image composition.
9. Future providers (Malevich / historian / stylist) можно добавить без переписывания ядра.
10. Есть unit, integration и product tests.

---

# 28. Definition of Done

Этап реализован корректно, если:
- knowledge layer реально стал общей typed runtime abstraction;
- parser upgrade полноценно используется downstream;
- `style_ingestion` provider стал первым сильным canonical provider;
- reasoning, profile и voice больше не зависят напрямую от parser SQL details;
- система готова к безопасному расширению новыми knowledge sources;
- дальнейшее подключение Malevich / historian / stylist станет эволюцией архитектуры, а не аварийным рефакторингом.

---

# 29. Архитектурный итог этапа

После реализации обновлённого Этапа 5 система получает не просто “папку с текстами”, а полноценную **knowledge fabric**, где:

- parser превращает source text в semantic-distilled style knowledge;
- style provider превращает это знание в runtime-friendly knowledge units;
- reasoning строит ответ на typed knowledge bundles;
- profile layer выравнивает их под пользователя;
- voice layer формулирует enriched meaning;
- generation получает richer, more controllable handoff.

Именно это делает knowledge layer не “подготовкой на будущее”, а **центральным runtime слоем**, без которого fashion reasoning assistant не сможет быть масштабируемым, управляемым и действительно умным.
