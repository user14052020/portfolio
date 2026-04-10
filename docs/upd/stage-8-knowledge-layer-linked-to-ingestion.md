
# Этап 8. Добавить knowledge layer вместо надежды на «умную модель»

## Контекст этапа

В основном архитектурном плане проекта Этап 8 сформулирован как переход от надежды на “умную модель” к явному **fashion knowledge layer**. В плане прямо указано, что бот должен:
- использовать базу стилей как источник знаний;
- извлекать знания из групп `style_catalog`, `color_theory`, `fashion_history`, `tailoring_principles`, `materials_fabrics`, `flatlay_prompt_patterns`;
- выполнять retrieval **до** вызова LLM;
- опираться на собственные данные проекта, а не только на память модели. ([Основной план, Этап 8](https://raw.githubusercontent.com/user14052020/portfolio/main/docs/upd/portfolio_chatbot_architecture_plan.md))

Критически важно, что у проекта уже есть **Этап 0** — отдельный ingestion pipeline, который:
- берёт запись из базы стилей;
- ищет описание на доверенных сайтах;
- парсит текст;
- нормализует структуру;
- извлекает признаки стиля;
- сохраняет результат в БД;
- логирует источник и дату обновления. ([Основной план, Этап 0](https://raw.githubusercontent.com/user14052020/portfolio/main/docs/upd/portfolio_chatbot_architecture_plan.md))

То есть Этап 8 не должен проектироваться как “когда-нибудь появится knowledge base”, а как слой, который **уже опирается** на существующий parser/ingestion pipeline и связывает Этапы 1–7 с уже накопленными style records.

---

# 1. Цель этапа

Сделать так, чтобы дальше вся чат-система, orchestrator, сценарии, anti-repeat и prompt builder работали **не от случайной памяти LLM**, а от собственного knowledge layer проекта.

После Этапа 8 система должна:
- использовать знания о стиле, а не только генерировать по ассоциациям модели;
- извлекать релевантные карточки знаний до reasoning;
- подмешивать в reasoning и prompt-building уже нормализованные данные из БД;
- работать поверх реально существующего ingestion слоя;
- быть расширяемой: новые источники, новые knowledge groups, новые retrieval strategies без переписывания chat runtime.

---

# 2. Архитектурная проблема без knowledge layer

Без явного knowledge layer даже хороший orchestrator и хороший prompt builder остаются ограничены:

1. **LLM не является надёжным источником фактов**
   - она может путать исторические референсы;
   - упрощать цветовую теорию;
   - “галлюцинировать” style logic.

2. **Стили плохо различаются**
   - особенно когда нужно объяснимо выбрать новый стиль;
   - особенно в `style_exploration`.

3. **Команды слишком зависят от общего качества модели**
   - `garment_matching` становится поверхностным;
   - `occasion_outfit` теряет уместность;
   - `style_exploration` становится повторяющимся.

4. **Ты уже инвестировал в ingestion pipeline**
   - если runtime не использует эти данные, значительная часть архитектурной ценности Этапа 0 пропадает.

---

# 3. Главный принцип этапа

## Knowledge layer = обязательный вход в reasoning pipeline

После этого этапа должен действовать такой принцип:

```text
User message / command
→ scenario context
→ retrieval from project knowledge layer
→ fashion reasoning
→ structured fashion brief
→ image prompt compiler
→ generation payload
```

А не так:

```text
User message
→ LLM "вспомни сама всё про стиль, цвет, историю, крой"
→ длинный prompt
→ hope for the best
```

---

# 4. Связь Этапа 8 с уже созданными этапами

## 4.1. Связь с Этапом 0
Этап 0 уже создал фундамент:
- parser / ingestion pipeline;
- style source ingestion;
- style normalization;
- trait extraction;
- запись в БД.

Следовательно, Stage 8 обязан считать:
- `style_catalog` и style knowledge records уже существующим слоем;
- parser — не частью chat runtime, а отдельным upstream supplier знаний;
- retrieval — downstream consumer этих данных.

## 4.2. Связь с Этапом 1
`ChatModeContext` должен хранить не только сценарное состояние, но и:
- `style_history`
- `current_style_id`
- `last_retrieved_knowledge_refs`
- `last_generation_prompt`
- `last_generated_outfit_summary`

Knowledge layer должен уметь подмешиваться в `ChatModeContext` и использоваться всеми режимами.

## 4.3. Связь с Этапом 3
Explicit orchestrator должен не “опционально подмешивать знания”, а считать retrieval частью application pipeline:
- определить active mode;
- собрать retrieval query;
- запросить knowledge layer;
- передать найденные knowledge cards в fashion reasoning.

## 4.4. Связь с Этапами 4–6
- `garment_matching` использует garment-aware retrieval;
- `occasion_outfit` использует occasion-aware retrieval;
- `style_exploration` использует style graph / traits / anti-repeat retrieval.

## 4.5. Связь с Этапом 7
Новый `FashionBrief` должен строиться не только из user context, но и из:
- style profile cards
- color theory cards
- tailoring notes
- materials/fabrics cards
- historical reference cards
- flatlay prompt patterns

То есть Stage 8 — это missing link между parser/DB и новым prompt pipeline.

---

# 5. Архитектурные принципы реализации

## 5.1. Clean Architecture

### Domain layer
Содержит:
- `KnowledgeCard`
- `KnowledgeQuery`
- `KnowledgeBundle`
- `KnowledgeType`
- `RetrievalIntent`
- value objects для style traits, color notes, tailoring notes, material notes

### Application layer
Содержит:
- `KnowledgeRetrievalService`
- `BuildKnowledgeQueryUseCase`
- `ResolveKnowledgeBundleUseCase`
- `RankKnowledgeCardsUseCase`
- `InjectKnowledgeIntoReasoningUseCase`

### Infrastructure layer
Содержит:
- repositories для style DB;
- adapters к ingestion-produced tables;
- search/index adapters;
- ranking/scoring adapters;
- caches;
- optional vector / lexical search implementation.

### Interface layer
Содержит:
- admin/debug endpoints для preview retrieved knowledge;
- serializers для knowledge bundle inspection;
- observability endpoints / traces.

---

## 5.2. SOLID

### Single Responsibility
- parser наполняет базу, но не занимается chat retrieval;
- repository читает knowledge records, но не принимает fashion decisions;
- retrieval service выбирает релевантные записи;
- ranking service сортирует;
- orchestrator использует результат, но не знает storage details.

### Open/Closed
Новые группы знаний (`dress_code_rules`, `body_proportion_rules`, `regional_style_notes`) добавляются без переписывания orchestrator и handlers.

### Liskov
Все источники knowledge должны быть взаимозаменяемыми по контракту:
- SQL-based provider
- Elasticsearch-based provider
- hybrid provider
- cached provider

### Interface Segregation
Нужны отдельные интерфейсы:
- `StyleCatalogRepository`
- `ColorTheoryRepository`
- `TailoringPrinciplesRepository`
- `FashionHistoryRepository`
- `FlatlayPatternsRepository`
- `KnowledgeRetrievalService`

### Dependency Inversion
Application layer зависит от `KnowledgeProvider`/`KnowledgeRetrievalService`, а не от конкретного Postgres / Elasticsearch / ORM.

---

## 5.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    knowledge/
      entities/
      value_objects/
      enums/
      policies/
  application/
    knowledge/
      services/
        knowledge_retrieval_service.py
        knowledge_bundle_builder.py
        knowledge_ranker.py
      use_cases/
        build_knowledge_query.py
        resolve_knowledge_bundle.py
        inject_knowledge_into_reasoning.py
  infrastructure/
    knowledge/
      repositories/
      search/
      caches/
      adapters/
    persistence/
  interfaces/
    api/
      routes/
      serializers/
```

И связка с уже существующим ingestion слоем:

```text
apps/backend/app/
  ingestion/
    ... (существующий parser / enrichment pipeline upstream)
  application/knowledge/
    ... (runtime retrieval downstream)
```

---

# 6. Что считать knowledge layer в этом проекте

Stage 8 должен опираться на 6 групп знаний, прямо перечисленных в основном плане:

1. `style_catalog`
2. `color_theory`
3. `fashion_history`
4. `tailoring_principles`
5. `materials_fabrics`
6. `flatlay_prompt_patterns`

([Основной план, Этап 8](https://raw.githubusercontent.com/user14052020/portfolio/main/docs/upd/portfolio_chatbot_architecture_plan.md))

Но из-за уже существующего parser/ingestion pipeline эти группы надо трактовать так:

## 6.1. `style_catalog`
Это уже не “идея на будущее”, а слой, который должен читаться из БД, наполняемой ingestion pipeline:
- canonical style name
- aliases
- summary
- traits
- palette
- garments
- materials
- relations
- restrictions / anti-mix notes
- visual identity

## 6.2. `color_theory`
На первом шаге это может быть:
- отдельная knowledge table;
- curated notes;
- вручную заведённые records.

Но retrieval должен строиться по тем же контрактам, что и для style records.

## 6.3. `fashion_history`
Точно так же:
- отдельные cards / notes;
- исторические референсы;
- происхождение style family;
- эпохи и культурный контекст.

## 6.4. `tailoring_principles`
Knowledge cards о:
- силуэте;
- пропорциях;
- формальности;
- посадке;
- балансировке вещи в образе.

## 6.5. `materials_fabrics`
Knowledge cards:
- о тканях;
- текстурах;
- сочетаемости;
- сезонности;
- визуальном поведении в flat lay.

## 6.6. `flatlay_prompt_patterns`
Отдельный набор cards/patterns:
- layout archetypes
- background families
- object density hints
- camera distance hints
- composition heuristics

---

# 7. Учитываем уже существующий parser / ingestion

Это ключевая часть Stage 8.

## 7.1. Что уже делает parser
Согласно Этапу 0 и документу про parser, ingestion pipeline:
- читает записи стилей из базы;
- ищет trusted sources;
- парсит и нормализует содержимое;
- извлекает признаки;
- сохраняет подробные данные о стиле в БД;
- ведёт source logging / freshness / updates.

То есть retrieval layer не должен пытаться “заменить парсер”. Он должен использовать его результат как source-of-truth.

## 7.2. Архитектурный принцип
Parser = **upstream data acquisition**  
Knowledge layer = **runtime consumption of normalized knowledge**

Они не должны быть смешаны.

## 7.3. Практический вывод
Начиная с Этапа 8, все runtime сценарии должны думать так:

- мы не “вспоминаем стиль” через модель;
- мы **читаем стиль из базы знаний**, уже наполненной parser’ом;
- LLM reasoning работает поверх retrieved knowledge cards.

---

# 8. Центральные доменные объекты knowledge layer

## 8.1. KnowledgeType

```python
class KnowledgeType(str, Enum):
    STYLE_CATALOG = "style_catalog"
    COLOR_THEORY = "color_theory"
    FASHION_HISTORY = "fashion_history"
    TAILORING_PRINCIPLES = "tailoring_principles"
    MATERIALS_FABRICS = "materials_fabrics"
    FLATLAY_PROMPT_PATTERNS = "flatlay_prompt_patterns"
```

## 8.2. KnowledgeCard

```python
class KnowledgeCard(BaseModel):
    id: str
    knowledge_type: KnowledgeType
    title: str
    summary: str
    body: str | None = None
    tags: list[str] = []
    style_id: str | None = None
    source_ref: str | None = None
    confidence: float = 1.0
    freshness: str | None = None
    metadata: dict = Field(default_factory=dict)
```

## 8.3. KnowledgeQuery

```python
class KnowledgeQuery(BaseModel):
    mode: str
    style_id: str | None = None
    style_name: str | None = None
    anchor_garment: dict | None = None
    occasion_context: dict | None = None
    diversity_constraints: dict = Field(default_factory=dict)
    intent: str | None = None
    limit: int = 10
```

## 8.4. KnowledgeBundle

```python
class KnowledgeBundle(BaseModel):
    style_cards: list[KnowledgeCard] = []
    color_cards: list[KnowledgeCard] = []
    history_cards: list[KnowledgeCard] = []
    tailoring_cards: list[KnowledgeCard] = []
    materials_cards: list[KnowledgeCard] = []
    flatlay_cards: list[KnowledgeCard] = []
    retrieval_trace: dict = Field(default_factory=dict)
```

---

# 9. Retrieval должен быть mode-aware

Knowledge retrieval не может быть одинаковым для всех сценариев.

## 9.1. `general_advice`
Приоритет:
- style catalog
- color theory
- tailoring principles

## 9.2. `garment_matching`
Приоритет:
- style_catalog по garment traits
- tailoring_principles
- materials_fabrics
- color_theory

Goal:
- подобрать гармоничный образ вокруг anchor garment.

## 9.3. `occasion_outfit`
Приоритет:
- style_catalog по occasion fit
- tailoring principles
- color theory
- fashion history (если нужен интеллектуальный слой)
- materials/fabrics по сезону и формальности

Goal:
- подобрать уместный образ под событие.

## 9.4. `style_exploration`
Приоритет:
- style_catalog
- style relations / traits
- fashion history
- flatlay prompt patterns
- anti-repeat aware retrieval

Goal:
- выбрать новое стилевое направление и не повторить прошлое.

---

# 10. Style catalog должен стать first-class dependency

## 10.1. Что это означает
Во всех последующих этапах:
- orchestrator,
- mode handlers,
- anti-repeat,
- prompt builder

должны считать `style_catalog` обязательной зависимостью.

## 10.2. Почему это важно
Именно style catalog, построенный ingestion pipeline, позволяет:
- объяснимо различать стили;
- не гадать style identity;
- строить candidate selection;
- делать anti-repeat не по “ощущению модели”, а по traits.

## 10.3. Что retrieval должен уметь для style catalog
- fetch by style_id
- fetch by style_name / alias
- fetch related styles
- fetch by traits
- fetch by palette
- fetch by garment family
- fetch by formality / seasonality / occasion fit

---

# 11. Связь knowledge layer с orchestrator

## 11.1. Новый обязательный шаг orchestrator
С Этапа 8 orchestrator должен работать так:

```text
load ChatModeContext
→ resolve active mode
→ build KnowledgeQuery
→ fetch KnowledgeBundle
→ build scenario reasoning input
→ invoke FashionReasoning
→ get FashionBrief
→ compile prompt
→ enqueue generation if needed
```

## 11.2. Что orchestrator больше не делает
Он не надеется, что LLM “сама знает”:
- стиль;
- цветовую теорию;
- tailoring notes;
- visual identity.

Он получает эти знания через retrieval service.

---

# 12. Связь knowledge layer с Этапом 6 (anti-repeat)

## 12.1. Почему это критично
Этап 6 ввёл persistent `style_history` и `diversity_constraints`, но без knowledge layer их качество ограничено.

## 12.2. Что меняется после Stage 8
Теперь anti-repeat может строиться не только от session memory, но и от `style_traits` / `style_profiles`, already populated by parser.

Например:
- avoid palette → сравнение с реальной palette карточки стиля;
- avoid hero garments → сравнение с extracted garments;
- force material contrast → выбор style candidate с другими materials;
- force silhouette shift → поиск стилей с другой silhouette family.

## 12.3. Вывод
Stage 8 делает anti-repeat не эвристикой поверх prompt, а knowledge-driven политикой.

---

# 13. Связь knowledge layer с Этапом 7 (prompt builder)

## 13.1. Новый prompt builder теперь зависит от retrieval
`FashionBrief` должен строиться из:
- scenario context
- user context
- style history
- diversity constraints
- **KnowledgeBundle**

## 13.2. Mapping в FashionBrief
Например:
- `style_identity` ← style catalog card
- `historical_reference` ← fashion history cards
- `tailoring_logic` ← tailoring cards
- `color_logic` ← color theory cards
- `materials` ← materials/fabrics cards
- `composition_rules` ← flatlay prompt patterns
- `negative_constraints` ← style restrictions + diversity constraints

## 13.3. Архитектурный смысл
Prompt builder перестаёт быть “ещё одним LLM prompt” и становится compiler над retrieved knowledge.

---

# 14. Что должен делать KnowledgeRetrievalService

## 14.1. Основной контракт

```python
class KnowledgeRetrievalService(Protocol):
    async def retrieve(self, query: KnowledgeQuery) -> KnowledgeBundle:
        ...
```

## 14.2. Ответственность
Сервис должен:
- принимать mode-aware query;
- ходить в нужные repositories;
- собирать cards по группам знаний;
- ранжировать их;
- возвращать компактный bundle для reasoning.

## 14.3. Что он не должен делать
- не вызывает generation;
- не пишет в parser tables;
- не решает сценарную state machine;
- не компилирует image prompt;
- не заменяет orchestrator.

---

# 15. Ranking и relevance

## 15.1. Почему нужно ранжирование
Если просто брать “всё, что есть в базе”, reasoning утонет в шуме.

## 15.2. Базовые правила ranking
- выше релевантность current mode;
- выше совпадение по style_id/style_name;
- выше совпадение по garment traits;
- выше совпадение по occasion slots;
- выше свежесть / confidence источника;
- выше полезность для данного stage flow.

## 15.3. Важно
Ranking должен быть частью knowledge layer, а не prompt builder.

---

# 16. Storage и search strategy

## 16.1. Базовый путь
На первом production-ready этапе knowledge layer может работать:
- через Postgres repositories;
- через индексированные таблицы;
- с optional Elasticsearch/keyword search для retrieval.

## 16.2. Почему этого достаточно
Потому что parser уже пишет нормализованные данные в БД.
Не нужно сразу усложнять систему векторными базами, если structured retrieval по style_id / traits / tags уже покрывает сценарии.

## 16.3. Но архитектура должна быть готова к росту
Добавить later:
- Elasticsearch ranking
- hybrid lexical + structured retrieval
- embeddings only if действительно понадобятся

---

# 17. Frontend и knowledge layer

Frontend не должен знать детали retrieval, но для support/debug полезно предусмотреть:
- debug panel “какие knowledge cards использовались”
- admin preview retrieved bundle
- trace id / bundle id в generation metadata

Так можно будет объяснимо отлаживать:
- почему бот выбрал именно этот стиль;
- почему подобрал именно такую палитру;
- почему дал такой исторический референс.

---

# 18. Observability

## 18.1. Что логировать
На каждый retrieval:
- `session_id`
- `message_id`
- `mode`
- `knowledge_query_hash`
- `style_id`
- `style_name`
- `retrieved_style_cards_count`
- `retrieved_color_cards_count`
- `retrieved_history_cards_count`
- `retrieved_tailoring_cards_count`
- `retrieved_material_cards_count`
- `retrieved_flatlay_cards_count`
- `knowledge_bundle_hash`

## 18.2. Метрики
- retrieval success rate
- empty knowledge bundle rate
- average bundle size
- average latency per knowledge group
- % scenarios using style_catalog
- % scenarios using tailoring/color/history cards
- effect on generation success / answer quality

---

# 19. Тестирование

## 19.1. Unit tests
Покрыть:
- `KnowledgeQuery` builders
- repositories
- ranking policies
- bundle builder
- mode-aware retrieval paths

## 19.2. Integration tests
Покрыть:
- style_exploration retrieves style + history + flatlay
- garment_matching retrieves garment-aware style/tailoring/material cards
- occasion_outfit retrieves occasion-relevant style/color/tailoring cards
- prompt builder receives non-empty bundle

## 19.3. E2E сценарии
Минимальный набор:
1. `style_exploration` использует style_catalog вместо пустого generic reasoning
2. `garment_matching` подбирает образ на основе anchor garment + retrieved knowledge
3. `occasion_outfit` использует slot context + retrieved occasion/style logic
4. retrieval survives provider fallback
5. anti-repeat использует traits из knowledge layer

---

# 20. Рекомендуемая модульная структура

```text
domain/knowledge/
  entities/
    knowledge_card.py
    knowledge_bundle.py
    knowledge_query.py
  enums/
    knowledge_type.py

application/knowledge/
  services/
    knowledge_retrieval_service.py
    knowledge_bundle_builder.py
    knowledge_ranker.py
  use_cases/
    build_knowledge_query.py
    resolve_knowledge_bundle.py
    inject_knowledge_into_reasoning.py

infrastructure/knowledge/
  repositories/
    style_catalog_repository.py
    color_theory_repository.py
    fashion_history_repository.py
    tailoring_principles_repository.py
    materials_fabrics_repository.py
    flatlay_patterns_repository.py
  search/
    knowledge_search_adapter.py
  caches/
    knowledge_cache.py
```

И связка с parser:

```text
ingestion/ (existing upstream)
→ normalized style tables
→ knowledge repositories
→ retrieval service
→ orchestrator / handlers / prompt builder
```

---

# 21. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- пытаться “встроить parser в chat backend”;
- продолжать полагаться на LLM как главный источник style facts;
- тянуть в prompt builder прямые SQL запросы;
- смешивать retrieval и generation queue;
- делать knowledge injection ad hoc строками без `KnowledgeBundle`;
- считать style DB опциональной для `style_exploration`.

---

# 22. Пошаговый план реализации Этапа 8

## Подэтап 8.1. Зафиксировать `KnowledgeCard`, `KnowledgeQuery`, `KnowledgeBundle`
Создать центральные domain entities.

## Подэтап 8.2. Поднять repositories поверх уже существующих parser tables
Сделать runtime read layer, который читает данные, уже подготовленные ingestion pipeline.

## Подэтап 8.3. Реализовать `KnowledgeRetrievalService`
Mode-aware retrieval с grouping и ranking.

## Подэтап 8.4. Встроить retrieval в orchestrator
Перед reasoning всегда строить `KnowledgeQuery` и получать `KnowledgeBundle`.

## Подэтап 8.5. Подключить `KnowledgeBundle` к `FashionBrief`
Prompt pipeline из Stage 7 теперь получает не пустой generic context, а реальные cards.

## Подэтап 8.6. Связать anti-repeat с knowledge traits
Stage 6 начинает использовать реальные style records, а не только session memory.

## Подэтап 8.7. Добавить observability и тесты
Сделать retrieval прозрачным.

---

# 23. Критерии готовности этапа

Этап 8 реализован корректно, если:

1. Chat runtime использует уже существующую базу стилей, наполняемую parser/ingestion pipeline.
2. Retrieval выполняется до fashion reasoning.
3. `style_catalog` стал обязательной зависимостью runtime, а не идеей на будущее.
4. `KnowledgeBundle` используется в orchestrator и prompt builder.
5. `garment_matching`, `occasion_outfit`, `style_exploration` имеют разные retrieval paths.
6. Anti-repeat начинает использовать реальные style traits из БД.
7. Prompt builder получает структурированные knowledge cards.
8. Parser и chat runtime разделены как upstream/downstream процессы.
9. Knowledge layer покрыт unit / integration / e2e тестами.
10. Система меньше зависит от случайной “эрудиции” модели.

---

# 24. Архитектурный итог этапа

После реализации Этапа 8 проект переходит:
- от системы, которая надеется на “умную модель”,
- к системе, которая использует собственный knowledge layer как first-class dependency.

Это связывает уже сделанный Этап 0 со всеми предыдущими этапами 1–7:

- Этап 1 получает содержательный `ChatModeContext`
- Этап 3 получает реальный retrieval input в orchestrator
- Этап 4 и 5 получают domain-aware рекомендации
- Этап 6 получает anti-repeat поверх style traits
- Этап 7 получает содержательный `FashionBrief`

Именно после такого изменения бот начинает отвечать как проект со своей базой знаний, а не как просто LLM с красивым тоном.
