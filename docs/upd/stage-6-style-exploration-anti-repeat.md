
# Этап 6. Исправить «Попробовать другой стиль» через анти-повтор

## Контекст этапа

В архитектурном плане проекта Этап 6 сформулирован как исправление режима **«Попробовать другой стиль»** через анти-повтор. В самом плане зафиксировано, что для `style_exploration` необходимо:
- хранить persistent `style_history` в session state;
- сохранять последние 3–5 `style directions`;
- строить в decision layer явные `diversity constraints`;
- разделять `semantic diversity` и `visual diversity`;
- гарантировать, что история предыдущих стилей не теряется между decision layer, structured brief, final generation prompt и Comfy input. 

Этот этап опирается на:
- **Этап 0** — ingestion pipeline и knowledge base стилей;
- **Этап 1** — доменная модель, `ChatModeContext`, state machine;
- **Этап 2** — тонкий frontend;
- **Этап 3** — explicit orchestrator;
- **Этап 7** будущего плана — двухслойный prompt builder, который позже станет более формализованным, но уже сейчас должен получать корректный diversity-aware brief.

---

# 1. Цель этапа

Превратить команду `style_exploration` из сценария, где:

- выбирается новый стиль или seed style;
- формально меняется random seed;
- но картинка остаётся почти той же по палитре, одежде и композиции;

в полноценный **diversity-aware сценарий**, где:

- система помнит предыдущие стилевые направления;
- различает **semantic diversity** и **visual diversity**;
- строит анти-повтор на уровне доменных признаков, а не на уровне надежды на случайность;
- генерирует осмысленно новый образ;
- может объяснимо контролировать, чем новый результат отличается от предыдущего;
- остаётся масштабируемой при росте базы стилей и числа режимов.

---

# 2. Архитектурная проблема текущей реализации

Симптом из плана: следующая картинка почти повторяет предыдущую — те же цвета, похожие вещи, та же композиция. Это значит, что текущая система не считает "новый стиль" отдельной доменной задачей с контролируемым отличием. 

Типовые причины:
1. `style_exploration` не хранит полноценную историю предыдущих style directions;
2. diversity обеспечивается только новым seed или новым style name;
3. history существует, но теряется между сервисами;
4. LLM не получает строгих anti-repeat constraints;
5. prompt builder не различает semantic и visual diversity;
6. Comfy workflow не получает информацию о том, **что именно нельзя повторять**;
7. нет метрик и логов, которые показывают, был ли стиль реально новым.

Этап 6 должен устранить эти причины на уровне архитектуры, а не через случайные усиления промпта.

---

# 3. Архитектурные принципы реализации

## 3.1. Clean Architecture

### Domain layer
Содержит:
- `StyleDirection`
- `StyleHistory`
- `DiversityConstraints`
- `StyleExplorationState`
- `SemanticDiversityPolicy`
- `VisualDiversityPolicy`

### Application layer
Содержит:
- `StyleExplorationHandler`
- `BuildStyleDirectionUseCase`
- `BuildDiversityConstraintsUseCase`
- `SelectCandidateStyleUseCase`
- `BuildStyleExplorationBriefUseCase`
- orchestration generation trigger

### Infrastructure layer
Содержит:
- style history persistence;
- style knowledge retrieval;
- LLM reasoning adapters;
- prompt compiler adapters;
- generation queue adapters;
- metadata persistence for generated results.

### Interface layer
Содержит:
- API contracts;
- DTO serializers;
- frontend command payload;
- response mappers.

## 3.2. SOLID

### Single Responsibility
- history storage отвечает только за хранение прошлых style directions;
- semantic diversity policy отвечает только за смысловое отличие;
- visual diversity policy отвечает только за layout/preset отличие;
- handler отвечает только за сценарий `style_exploration`;
- prompt compiler отвечает только за превращение brief в generation payload.

### Open/Closed
Новый тип diversity constraints или новый visual preset должен добавляться без переписывания orchestrator целиком.

### Liskov
`StyleExplorationHandler` должен быть совместим с общим интерфейсом mode handlers.

### Interface Segregation
Вместо одного жирного “style service” нужны отдельные интерфейсы:
- `StyleHistoryStore`
- `CandidateStyleSelector`
- `StyleKnowledgeProvider`
- `SemanticDiversityBuilder`
- `VisualDiversityBuilder`
- `StyleExplorationBriefBuilder`
- `GenerationJobScheduler`

### Dependency Inversion
Application layer зависит от абстракций, а не от конкретного Redis/DB/vLLM/ComfyUI.

## 3.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    style_exploration/
      entities/
      enums/
      policies/
      value_objects/
  application/
    stylist_chat/
      handlers/
        style_exploration_handler.py
      use_cases/
        start_style_exploration.py
        build_diversity_constraints.py
        build_style_exploration_brief.py
        persist_style_direction.py
      services/
        style_history_service.py
        candidate_style_selector.py
        semantic_diversity_service.py
        visual_diversity_service.py
  infrastructure/
    llm/
    knowledge/
    queue/
    persistence/
  interfaces/
    api/
      routes/
      serializers/
```

Рекомендуемая frontend/FSD-структура:

```text
src/
  entities/
    style-direction/
    command/
    generation-job/
  features/
    run-style-exploration-command/
    retry-style-exploration/
  widgets/
    style-exploration-entry/
    style-generation-status/
  processes/
    stylist-chat/
```

---

# 4. Доменная модель `style_exploration`

## 4.1. Главная сущность: StyleDirection

`StyleDirection` — это не просто имя стиля, а нормализованное описание одного реально использованного направления генерации.

### Рекомендуемая модель

```python
class StyleDirection(BaseModel):
    style_id: str | None = None
    style_name: str
    style_family: str | None = None
    palette: list[str] = []
    silhouette_family: str | None = None
    hero_garments: list[str] = []
    footwear: list[str] = []
    accessories: list[str] = []
    materials: list[str] = []
    styling_mood: list[str] = []
    composition_type: str | None = None
    background_family: str | None = None
    layout_density: str | None = None
    camera_distance: str | None = None
    visual_preset: str | None = None
    created_at: datetime | None = None
```

## 4.2. Почему это важно
Без `StyleDirection` система не может:
- сравнивать предыдущие и текущие результаты;
- строить anti-repeat constraints;
- объяснять, чем новый стиль отличается;
- логировать реальное разнообразие;
- переиспользовать history в будущем.

---

# 5. Persistent style history

## 5.1. Требование плана
План прямо говорит: в session state нужно хранить последние 3–5 style directions. 

## 5.2. Где должна жить history
`style_history` не должна существовать только:
- во фронтенде;
- в последнем ответе LLM;
- в prompt builder локально;
- в metadata Comfy результата.

Она должна жить в backend session state / persistence layer.

### Варианты хранения
- JSONB в таблице chat session context;
- отдельная таблица `style_exploration_history`;
- Redis-кэш + durable snapshot в БД.

Для масштабируемости лучший вариант:
- durable source of truth в БД;
- кэш в Redis опционально.

## 5.3. Что должно храниться
Последние 3–5 записей по каждой active session:
- `palette`
- `silhouette_family`
- `hero_garments`
- `footwear`
- `accessories`
- `materials`
- `styling_mood`
- `composition_type`
- `background_family`
- `visual_preset`

Именно это перечислено в плане как ядро anti-repeat memory.

---

# 6. Разделить semantic diversity и visual diversity

## 6.1. Почему это ключевое требование
План прямо фиксирует, что смены random seed недостаточно. Нужны два уровня разнообразия:
1. `semantic diversity`
2. `visual diversity`

## 6.2. Semantic diversity
Это отличие по смыслу, стилевому содержанию и набору элементов.

### Примеры признаков
- другая палитра;
- другой силуэт;
- другой набор ключевых вещей;
- другая обувь;
- другая аксессуарная логика;
- другие материалы;
- другое стилистическое настроение;
- другой style family или соседняя family.

### Примеры
Плохо:
- тот же пиджак, та же рубашка, те же лоферы, только seed другой

Хорошо:
- вместо tailored dark academia → relaxed soft modernist
- вместо camel/navy/cream → washed olive/charcoal/off-white
- вместо loafers → clean derby / boots
- вместо blazer + pleated trousers → overshirt + wide trousers

## 6.3. Visual diversity
Это отличие по способу визуальной подачи.

### Примеры признаков
- другой layout archetype;
- другая background family;
- другая spacing density;
- другая distance / framing;
- другой object spread;
- другая shadow hardness;
- другой anchor placement;
- другая композиционная иерархия.

### Примеры
Плохо:
- тот же flat lay layout с тем же расположением вещей

Хорошо:
- сменить compact editorial spread на airy catalog layout
- сменить marble surface на textured linen / dark wood
- сменить tight framing на wider overhead composition

## 6.4. Ключевой архитектурный вывод
Анти-повтор должен строиться **на двух независимых слоях**:
- semantic diversity constraints
- visual diversity constraints

Оба слоя должны потом доходить до generation payload.

---

# 7. DiversityConstraints как доменная сущность

## 7.1. Рекомендуемая модель

```python
class DiversityConstraints(BaseModel):
    avoid_palette: list[str] = []
    avoid_hero_garments: list[str] = []
    avoid_silhouette_families: list[str] = []
    avoid_composition_types: list[str] = []
    avoid_background_families: list[str] = []
    force_material_contrast: bool = False
    force_footwear_change: bool = False
    force_accessory_change: bool = False
    force_visual_preset_shift: bool = False
    target_semantic_distance: str | None = None
    target_visual_distance: str | None = None
```

## 7.2. Почему это нужно
План прямо указывает на `avoid previous palette`, `avoid previous hero garments`, `avoid previous silhouette family`, `avoid previous composition layout`, `force material contrast`, `force footwear change`, `force accessory change`. Это нельзя держать россыпью строк в prompt builder — нужна отдельная доменная сущность. 

---

# 8. Candidate style selection

## 8.1. Почему “просто взять другой style_name” недостаточно
Даже если у тебя в базе почти тысяча стилей, случайный выбор не гарантирует:
- смысловой новизны;
- визуальной новизны;
- близости к нужному семейству;
- качества результата.

## 8.2. Нужен отдельный use case
`SelectCandidateStyleUseCase` должен:
1. взять current style / seed style;
2. загрузить `style_history`;
3. загрузить knowledge relations по стилям;
4. выбрать кандидата, который:
   - не дублирует предыдущие направления;
   - сохраняет осмысленную связность;
   - подходит под desired diversity distance.

## 8.3. Источники для отбора
- `style_catalog`
- `style_relations`
- `style_profiles`
- `style_traits`
- `style_taxonomy_links`
- текущая сессия и её `style_history`

---

# 9. SemanticDiversityPolicy

## 9.1. Задача
Построить ограничения и/или target direction так, чтобы новый образ отличался по смысловым признакам.

## 9.2. Рекомендуемый контракт

```python
class SemanticDiversityPolicy(Protocol):
    async def build(
        self,
        history: list[StyleDirection],
        candidate_style: dict,
        session_context: dict | None = None,
    ) -> DiversityConstraints:
        ...
```

## 9.3. Базовые правила
Policy должен:
- запрещать повтор dominant palette из последних 1–2 генераций;
- запрещать повтор hero garments, если они были dominant;
- сдвигать silhouette family;
- менять material family;
- заставлять сменить footwear, если footwear типично совпадает;
- вводить accessory shift.

## 9.4. Не путать с LLM “пожеланием”
Это должны быть формальные constraints, а не надежда, что модель “может быть, сама не повторит”.

---

# 10. VisualDiversityPolicy

## 10.1. Задача
Контролировать визуальное отличие вне зависимости от semantic content.

## 10.2. Контракт

```python
class VisualDiversityPolicy(Protocol):
    async def build(
        self,
        history: list[StyleDirection],
        current_visual_presets: list[dict],
    ) -> DiversityConstraints:
        ...
```

## 10.3. Базовые правила
- не повторять recent composition type;
- не повторять recent background family;
- менять layout density;
- менять camera distance;
- менять visual preset;
- при повторе стиля всё равно обеспечивать visual delta.

---

# 11. StyleExplorationBrief

## 11.1. После выбора candidate style и constraints
Orchestrator должен строить `StyleExplorationBrief`, который уже содержит:
- выбранный или сгенерированный style direction;
- semantic diversity constraints;
- visual diversity constraints;
- связь с knowledge base;
- рекомендации для final prompt compiler.

### Рекомендуемая модель

```python
class StyleExplorationBrief(BaseModel):
    style_identity: str
    style_family: str | None = None
    style_summary: str
    historical_reference: list[str] = []
    tailoring_logic: list[str] = []
    color_logic: list[str] = []
    garment_list: list[str] = []
    palette: list[str] = []
    materials: list[str] = []
    footwear: list[str] = []
    accessories: list[str] = []
    styling_notes: list[str] = []
    composition_rules: list[str] = []
    negative_constraints: list[str] = []
    diversity_constraints: DiversityConstraints
```

## 11.2. Почему нужен отдельный brief
Потому что план прямо требует, чтобы history не терялась между:
- decision layer
- structured brief
- final generation prompt
- Comfy input.

---

# 12. Прокладка diversity до generation prompt

## 12.1. Критическое требование этапа
Даже если history и constraints построены, они бесполезны, если пропадают до final prompt. Это прямо указано в плане.

## 12.2. Архитектурное правило
Вся цепочка должна быть непрерывной:

```text
style_history
→ diversity_constraints
→ style_exploration_brief
→ prompt compiler
→ generation payload
→ ComfyUI workflow metadata
```

## 12.3. Что это значит practically
`previous_style_directions` и `DiversityConstraints` должны:
- сохраняться в `DecisionResult.telemetry/context_patch`;
- попадать в prompt builder input;
- попадать в final prompt / negative prompt / visual preset selection;
- логироваться вместе с generation job;
- сохраняться в metadata finished generation.

---

# 13. Prompt compiler и Comfy integration

## 13.1. Prompt compiler
Даже если полный двухслойный prompt builder будет формализован позже, уже на этом этапе `ImagePromptCompiler` должен уметь:
- принимать `StyleExplorationBrief`;
- отдельно учитывать semantic и visual constraints;
- строить стабильный generation payload.

## 13.2. Что должно уходить в payload
Минимум:
- final prompt
- negative prompt
- chosen visual preset
- palette tags
- garments tags
- diversity tags
- style id / style name

## 13.3. Comfy metadata
Нужно сохранять:
- `style_direction_id`
- `source_style_id`
- `palette`
- `visual_preset`
- `composition_type`
- `background_family`
- `diversity_constraints_hash`

Это пригодится для анализа повторов.

---

# 14. Что должен делать StyleExplorationHandler

## 14.1. Основной контракт

```python
class StyleExplorationHandler(ChatModeHandler):
    async def handle(
        self,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        ...
```

## 14.2. Ответственность handler
Он должен:
- запускать сценарий `style_exploration`;
- загружать `style_history`;
- выбирать candidate style;
- строить semantic/visual diversity constraints;
- собирать `StyleExplorationBrief`;
- вызывать prompt compiler;
- создавать generation job через scheduler;
- обновлять `style_history` после завершения или подготовки новой direction;
- возвращать `DecisionResult.text_and_generate`.

## 14.3. Что handler не должен делать
- напрямую работать с Comfy UI;
- вручную строить giant prompt через ad hoc string concatenation;
- прятать anti-repeat в одной ветке if;
- хранить history локально в памяти процесса как единственный source of truth.

---

# 15. Frontend после исправления сценария

## 15.1. Quick action
Frontend только инициирует:

```json
{
  "session_id": "...",
  "requested_intent": "style_exploration",
  "command_name": "style_exploration",
  "command_step": "start",
  "message": null
}
```

## 15.2. Что frontend не делает
- не решает, “достаточно ли новый” стиль;
- не выбирает новый seed style;
- не хранит style history как source of truth;
- не пытается анти-повторить локально.

## 15.3. Async generation UX
После `text_and_generate`:
1. показать текстовое описание нового направления;
2. показать pending image;
3. подписаться на `job_id`;
4. подтянуть результат;
5. optionally показать “чем этот стиль отличается от предыдущего”.

---

# 16. Persistence и устойчивость

## 16.1. Что хранить
Минимум:
- `style_history`
- `last_generated_outfit_summary`
- `last_generation_prompt`
- `current_style_id`
- `current_job_id`
- `last_decision_type`

## 16.2. Когда сохранять
1. До generation enqueue;
2. После выбора нового `StyleDirection`;
3. После получения `job_id`;
4. После завершения generation;
5. После recoverable error.

## 16.3. Почему это важно
Так предотвращаются:
- дубли generation jobs;
- потеря history;
- повтор одного и того же стиля после refresh/retry;
- расхождение между решением и финальным результатом.

---

# 17. Observability

## 17.1. Что логировать
На каждый `style_exploration` шаг:
- `session_id`
- `message_id`
- `style_id`
- `style_name`
- `resolved_mode`
- `decision_type`
- `style_history_size`
- `semantic_constraints_hash`
- `visual_constraints_hash`
- `palette`
- `hero_garments`
- `composition_type`
- `visual_preset`
- `generation_job_id`
- `provider`
- `fallback_used`

## 17.2. Метрики режима
- `% style_exploration flows ending in generation`
- repeat rate by palette
- repeat rate by hero garments
- repeat rate by silhouette family
- repeat rate by composition type
- mean semantic diversity score
- mean visual diversity score
- generation success rate per visual preset

Это позволит не гадать “похоже / не похоже”, а мерить разнообразие.

---

# 18. Тестирование

## 18.1. Unit tests
Покрыть:
- `StyleHistoryStore`
- candidate style selector
- semantic diversity policy
- visual diversity policy
- brief builder
- invariants “history reaches prompt builder”

## 18.2. Integration tests
Покрыть:
- first style exploration with empty history
- second style exploration with recent history
- repeat-prevention on palette
- repeat-prevention on hero garments
- propagation of constraints to generation payload

## 18.3. E2E сценарии
Минимальный набор:
1. первый `style_exploration` → generation
2. второй `style_exploration` → generation with different palette and silhouette
3. third run → visual preset changed
4. recoverable provider fallback but constraints preserved
5. refresh / retry does not lose style history

---

# 19. Рекомендуемая модульная структура

```text
domain/style_exploration/
  entities/
    style_direction.py
    style_history.py
    diversity_constraints.py
    style_exploration_brief.py
  policies/
    semantic_diversity_policy.py
    visual_diversity_policy.py
  enums/
    style_exploration_flow_state.py

application/stylist_chat/handlers/
  style_exploration_handler.py

application/stylist_chat/use_cases/
  start_style_exploration.py
  select_candidate_style.py
  build_diversity_constraints.py
  build_style_exploration_brief.py
  persist_style_direction.py

application/stylist_chat/services/
  style_history_service.py
  style_exploration_context_builder.py
  style_prompt_compiler.py

infrastructure/knowledge/
  style_knowledge_provider.py
  style_relations_provider.py

infrastructure/queue/
  generation_job_scheduler.py
```

---

# 20. Что не надо делать на этом этапе

Чтобы не сломать архитектуру, нельзя:
- лечить повтор просто увеличением random seed;
- пытаться решить проблему только “усилением промпта”;
- хранить style history только на фронтенде;
- считать различие стилей только по имени style;
- смешивать semantic и visual diversity в один неформализованный список строк;
- допускать потерю constraints между orchestrator и prompt builder;
- решать anti-repeat только на уровне Comfy workflow без decision-layer памяти.

---

# 21. Пошаговый план реализации Этапа 6

## Подэтап 6.1. Ввести `StyleDirection`
Создать доменную сущность и сериализацию.

## Подэтап 6.2. Реализовать persistent `style_history`
Сделать durable storage последних 3–5 направлений.

## Подэтап 6.3. Реализовать `CandidateStyleSelector`
Выбор style candidate с учётом history и style knowledge.

## Подэтап 6.4. Реализовать `SemanticDiversityPolicy`
Построение anti-repeat constraints на уровне смысла.

## Подэтап 6.5. Реализовать `VisualDiversityPolicy`
Построение anti-repeat constraints на уровне композиции и visual preset.

## Подэтап 6.6. Реализовать `StyleExplorationBrief`
Собрать structured brief с `diversity_constraints`.

## Подэтап 6.7. Протянуть constraints до final generation payload
Проверить, что history не теряется между orchestrator, brief, prompt builder и Comfy input.

## Подэтап 6.8. Добавить observability и тесты
Сделать сценарий измеримым.

---

# 22. Критерии готовности этапа

Этап 6 реализован корректно, если:

1. `style_exploration` хранит persistent `style_history`.
2. История содержит не только style name, но и реальные style directions.
3. Anti-repeat строится через `DiversityConstraints`, а не только через новый seed.
4. Semantic diversity и visual diversity разделены как отдельные policy layers.
5. `previous_style_directions` не теряются до самого generation payload.
6. Новый результат отличается по смысловым и визуальным признакам.
7. Generation metadata сохраняет данные для последующего анализа повторов.
8. Frontend получает стабильный `text_and_generate` flow.
9. Режим покрыт unit / integration / e2e тестами.
10. Код режима можно развивать независимо от других сценариев.

---

# 23. Архитектурный итог этапа

После реализации Этапа 6 команда **«Попробовать другой стиль»** перестаёт быть "почти тем же образом с другим сидом" и становится полноценным diversity-aware сценарием:

- с persistent memory;
- с anti-repeat на уровне домена;
- с разделением semantic и visual diversity;
- с knowledge-driven выбором нового направления;
- с протягиванием constraints до generation payload;
- с измеримостью качества;
- с высокой поддерживаемостью.

Именно после такого изменения можно дальше усиливать режим:
- richer style knowledge graph;
- ranking нескольких candidate directions;
- adaptive diversity distance;
- персонализацию по taste profile;
- выбор между “близким стилем” и “контрастным стилем”;
- аналитические отчёты по разнообразию генераций.
