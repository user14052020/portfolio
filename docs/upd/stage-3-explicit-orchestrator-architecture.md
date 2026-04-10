
# Этап 3. Переписать decision layer как явный orchestrator

## Контекст этапа

В архитектурном плане проекта Этап 3 сформулирован как необходимость выделить отдельный orchestration layer между API route и LLM/generation stack. План прямо требует:
- ввести отдельный `stylist_chat_orchestrator.py`;
- вынести в него решение о том, какой режим активен;
- определять, хватает ли контекста для генерации;
- решать, нужно ли уточнение;
- выбирать, какую память и knowledge base подмешивать;
- вызывать нужный prompt builder;
- создавать generation job;
- возвращать пользователю типизированный результат;
- ввести явный `DecisionResult` (`text_only`, `text_and_generate`, `clarification_required`, `error_recoverable`). citeturn153082view0

Этот этап опирается на:
- Этап 1 — где зафиксированы доменная модель, `ChatModeContext`, state machines и инварианты;
- Этап 2 — где frontend нормализован до тонкого UI и передаёт backend типизированный payload, а не содержит бизнес-логику.

---

## Цель этапа

Превратить текущий decision layer из неявной смеси:
- API route логики;
- LLM decision логики;
- prompt building;
- session state обработки;
- generation branching;
- fallback эвристик;

в **отдельный orchestrator**, который:
- читает и обновляет доменное состояние;
- понимает активный режим и стадию сценария;
- принимает типизированное решение;
- делегирует задачи специализированным сервисам;
- управляет переходом в generation jobs;
- формирует стабильный и тестируемый результат для API.

---

# 1. Зачем нужен explicit orchestrator

Сейчас типовая проблема таких систем в том, что ответственность размыта между:
- API route;
- conversational service;
- LLM wrapper;
- prompt builder;
- queue/job creation;
- fallback logic.

Когда всё это сплетено, появляются симптомы, которые у тебя уже есть:
1. follow-up может интерпретироваться как новый чат вместо продолжения сценария;
2. LLM что-то решил, но generation не запустилась;
3. решение и prompt потеряли контекст между сервисами;
4. после уточнения случается "тишина", потому что нет явного `DecisionResult`;
5. поведение невозможно надежно тестировать, потому что логика спрятана в ветвлениях, а не в контракте.

Explicit orchestrator нужен, чтобы:
- формализовать управление сценарием;
- изолировать бизнес-решения от транспорта и модели;
- повысить предсказуемость;
- упростить поддержку;
- сделать систему расширяемой.

---

# 2. Архитектурная роль orchestrator в Clean Architecture

## 2.1. Позиция слоя

В clean architecture orchestrator находится в **application layer**.

### Domain layer
Содержит:
- сущности (`ChatModeContext`, `AnchorGarment`, `OccasionContext`, `StyleDirection`);
- enums (`ChatMode`, `FlowState`, `ClarificationKind`);
- state machine rules;
- domain invariants;
- value objects;
- доменные интерфейсы.

### Application layer
Содержит:
- `StylistChatOrchestrator`;
- use cases;
- `DecisionResult`;
- orchestration policies;
- command handling;
- взаимодействие между domain и infrastructure.

### Infrastructure layer
Содержит:
- LLM adapters;
- vLLM client;
- ComfyUI client;
- repositories;
- queue/job backends;
- retrieval providers;
- knowledge adapters;
- logging/metrics.

### Interface layer
Содержит:
- API routes;
- DTO ↔ domain adapters;
- serializers.

## 2.2. Ключевой принцип
Orchestrator **не должен**:
- быть FastAPI route;
- напрямую знать про HTTP;
- быть обёрткой над одной LLM;
- сам рисовать prompt внутри if/else без выделенных сервисов;
- быть местом SQL-запросов и Comfy API вызовов "по месту".

Он должен координировать взаимодействие между зависимостями через интерфейсы.

---

# 3. SOLID-принципы для orchestrator

## S — Single Responsibility Principle
`StylistChatOrchestrator` отвечает только за orchestration:
- принять доменный input;
- загрузить состояние;
- выбрать сценарный путь;
- вызвать нужные сервисы;
- вернуть `DecisionResult`.

Он **не отвечает** за:
- парсинг HTML;
- прямую работу с БД;
- raw HTTP вызовы в ComfyUI;
- реализацию retrieval;
- форматирование промпта "вручную".

## O — Open/Closed Principle
Новый режим должен добавляться без переписывания orchestrator целиком.  
Подход:
- добавить новый mode handler;
- зарегистрировать новый use case / strategy;
- orchestrator остаётся закрыт для массовой переписи.

## L — Liskov Substitution Principle
Все mode handlers должны быть взаимозаменяемыми по одному интерфейсу.  
Например:
- `handle(context, command) -> DecisionResult`

## I — Interface Segregation Principle
Вместо одного жирного dependency graph нужны узкие интерфейсы:
- `ChatContextStore`
- `ModeResolver`
- `ClarificationPolicy`
- `KnowledgeProvider`
- `StyleHistoryProvider`
- `PromptBuilder`
- `GenerationJobScheduler`
- `LLMReasoner`
- `EventLogger`

## D — Dependency Inversion Principle
Orchestrator зависит от интерфейсов, а не от конкретных реализаций:
- не от `RedisQueue`;
- а от `GenerationJobScheduler`;
- не от `VllmClient`;
- а от `LLMReasoner`.

Это критично для тестирования и смены технологий.

---

# 4. FSD и декомпозиция backend-модулей

Хотя FSD чаще применяют к frontend, его принцип "делить по смысловым срезам" полезен и в backend как feature-oriented modularization.

Рекомендуемая структура:

```text
apps/backend/app/
  domain/
    chat/
      entities/
      enums/
      value_objects/
      state_machines/
      policies/
    style/
    generation/
  application/
    stylist_chat/
      orchestrator/
      use_cases/
      handlers/
      dto/
      contracts/
    generation_jobs/
    knowledge_retrieval/
  infrastructure/
    persistence/
    llm/
    comfy/
    queue/
    observability/
    search/
  interfaces/
    api/
      routes/
      serializers/
      adapters/
```

### Смысл
- `domain/` — правила и модели;
- `application/` — orchestration;
- `infrastructure/` — реализации адаптеров;
- `interfaces/` — HTTP/DTO слой.

---

# 5. Что такое decision layer после переписывания

Decision layer больше не должен быть "неявной цепочкой" из LLM вызова и нескольких if.  
Он должен стать **application service orchestration pipeline**:

1. Получить command/message input.
2. Загрузить `ChatModeContext`.
3. Разрешить активный режим.
4. Применить state machine.
5. Собрать необходимые knowledge inputs.
6. Выбрать prompt / reasoning path.
7. Получить reasoning result.
8. Принять decision:
   - text only
   - clarification
   - text + generate
   - error recoverable
9. При необходимости создать generation job.
10. Обновить `ChatModeContext`.
11. Вернуть типизированный `DecisionResult`.

---

# 6. Главные обязанности orchestrator

## 6.1. Вход
Принимать нормализованный доменный command:

```python
class ChatCommand:
    session_id: str
    message: str | None
    requested_intent: ChatMode | None
    command_name: str | None
    command_step: str | None
    asset_id: str | None
    metadata: dict | None
```

## 6.2. Разрешение режима
Orchestrator должен понимать:
- есть ли активный `ChatModeContext`;
- продолжает ли пользователь существующий сценарий;
- нужно ли уважать `requested_intent`;
- можно ли переключиться между режимами;
- что делать при конфликте между текущим flow и новым command.

## 6.3. Управление clarification
Если state machine указывает, что нужны уточнения, orchestrator:
- определяет `clarification_kind`;
- формирует один точный follow-up;
- обновляет state;
- возвращает `DecisionResult.clarification_required`.

## 6.4. Подготовка context assembly
Orchestrator должен уметь собирать inputs для reasoning:
- conversation memory;
- user profile;
- style history;
- occasion slots;
- anchor garment;
- retrieval from style knowledge;
- anti-repeat constraints;
- asset metadata;
- last generation context.

## 6.5. Делегирование reasoning
Orchestrator не должен сам быть "LLM brain".  
Он вызывает `LLMReasoner`, передавая структурированный input.

## 6.6. Управление generation
Если решение требует генерацию:
- orchestrator готовит `GenerationIntent`;
- вызывает `GenerationJobScheduler`;
- получает `job_id`;
- обновляет state;
- возвращает `DecisionResult.text_and_generate` или `generation_only`.

## 6.7. Recoverable error management
Если reasoning/generation временно недоступны:
- orchestrator формирует recoverable result;
- сохраняет контекст;
- не теряет сценарий;
- не уходит в silent failure.

---

# 7. Концепция mode handlers

Чтобы orchestrator не превратился в "гигантский switch", каждый режим должен иметь свой handler.

## 7.1. Интерфейс

```python
class ChatModeHandler(Protocol):
    async def handle(
        self,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        ...
```

## 7.2. Реализации
- `GeneralAdviceHandler`
- `GarmentMatchingHandler`
- `StyleExplorationHandler`
- `OccasionOutfitHandler`

## 7.3. Ответственность handler
Mode handler:
- знает логику конкретного сценария;
- использует state machine этого режима;
- собирает mode-specific reasoning input;
- выбирает mode-specific prompt builder;
- возвращает `DecisionResult`.

## 7.4. Роль orchestrator относительно handlers
`StylistChatOrchestrator`:
- выбирает handler;
- обеспечивает shared dependencies;
- управляет транзакцией состояния;
- логирует общие события.

---

# 8. DecisionResult как обязательный контракт

План прямо требует типизированный `DecisionResult`, чтобы устранить "тишину" после уточнений. citeturn153082view0

## 8.1. Рекомендуемая модель

```python
class DecisionType(str, Enum):
    TEXT_ONLY = "text_only"
    TEXT_AND_GENERATE = "text_and_generate"
    GENERATION_ONLY = "generation_only"
    CLARIFICATION_REQUIRED = "clarification_required"
    ERROR_RECOVERABLE = "error_recoverable"
    ERROR_HARD = "error_hard"
```

```python
class DecisionResult(BaseModel):
    decision_type: DecisionType
    active_mode: ChatMode
    flow_state: str
    reply_text: str | None = None
    clarification_kind: str | None = None
    generation_job_id: str | None = None
    generation_payload: dict | None = None
    context_patch: dict = Field(default_factory=dict)
    telemetry: dict = Field(default_factory=dict)
```

## 8.2. Архитектурный эффект
Любой handler обязан вернуть один из допустимых исходов.  
У API layer больше нет права "догадаться", что делать дальше.

## 8.3. Почему это критично
Без типизированного результата:
- follow-up могут теряться;
- generation может не стартовать;
- фронтенд не понимает, что рендерить;
- логирование бесполезно.

---

# 9. Use cases внутри orchestrator

Вместо одного "умного" сервиса полезно мыслить use-case’ами.

## 9.1. Основной use case
`HandleStylistChatCommandUseCase`

Внутренние шаги:
1. `load_context`
2. `resolve_mode`
3. `apply_transition`
4. `delegate_to_handler`
5. `persist_context`
6. `schedule_generation_if_needed`
7. `return_decision`

## 9.2. Вспомогательные use cases
- `StartCommandFlowUseCase`
- `ContinueFlowUseCase`
- `RequestClarificationUseCase`
- `BuildReasoningContextUseCase`
- `ScheduleGenerationUseCase`
- `RecoverFromProviderErrorUseCase`

### Преимущество
Use cases проще тестировать, чем один монолитный метод на 600 строк.

---

# 10. Required interfaces (ports)

## 10.1. State / session
```python
class ChatContextStore(Protocol):
    async def load(self, session_id: str) -> ChatModeContext: ...
    async def save(self, context: ChatModeContext) -> None: ...
```

## 10.2. LLM reasoning
```python
class LLMReasoner(Protocol):
    async def decide(self, reasoning_input: dict) -> dict: ...
```

## 10.3. Prompt building
```python
class PromptBuilder(Protocol):
    async def build(self, brief: dict) -> dict: ...
```

## 10.4. Knowledge retrieval
```python
class KnowledgeProvider(Protocol):
    async def fetch(self, query: dict) -> dict: ...
```

## 10.5. Style history / anti-repeat
```python
class StyleHistoryProvider(Protocol):
    async def get_recent(self, session_id: str) -> list[dict]: ...
```

## 10.6. Generation scheduling
```python
class GenerationJobScheduler(Protocol):
    async def enqueue(self, payload: dict) -> str: ...
```

## 10.7. Event logging
```python
class EventLogger(Protocol):
    async def emit(self, event_name: str, payload: dict) -> None: ...
```

---

# 11. Сценарный pipeline по режимам

## 11.1. `general_advice`
1. Resolve active mode.
2. Build lightweight reasoning context.
3. Ask LLM for text answer.
4. Return `DecisionResult.text_only`.

### Особенность
По умолчанию здесь нет обязательной generation.

---

## 11.2. `garment_matching`
1. Если пришёл `command_step=start`:
   - перевести контекст в `awaiting_anchor_garment`;
   - вернуть clarification.
2. Если пришёл follow-up:
   - нормализовать `AnchorGarment`;
   - если данных мало → clarification;
   - если хватает → build outfit brief.
3. Подмешать:
   - profile context;
   - style knowledge;
   - occasion-neutral styling rules;
   - color/tailoring notes.
4. Получить reasoning result.
5. Создать generation job.
6. Вернуть `text_and_generate`.

### Важный инвариант
Если `anchor_garment` достаточен, режим обязан закончиться generation, а не просто текстом.

---

## 11.3. `style_exploration`
1. Determine seed style / current style.
2. Retrieve `style_history`.
3. Retrieve style profile + related styles.
4. Build diversity constraints:
   - avoid previous palette
   - avoid previous silhouette
   - avoid previous hero garments
   - avoid previous composition
5. Ask reasoner for new style brief.
6. Call prompt builder.
7. Create generation job.
8. Update style history.
9. Return `text_and_generate`.

### Ключевой смысл
Именно orchestrator должен гарантировать anti-repeat, а не надеяться, что LLM "сама догадается".

---

## 11.4. `occasion_outfit`
1. Если `command_step=start`:
   - перейти в `awaiting_occasion_details`;
   - вернуть первое уточнение.
2. Follow-up заполняет `OccasionContext`.
3. Проверить slot completeness.
4. Если слотов мало → clarification.
5. Если хватает:
   - build occasion outfit brief;
   - retrieve relevant style knowledge;
   - add dress-code / impression rules.
6. Create generation job.
7. Return `text_and_generate`.

### Важное правило
После заполнения минимального контекста orchestrator не имеет права вернуть "тишину" или уйти в свободный чат.

---

# 12. Prompt builder не должен жить внутри orchestrator

## 12.1. Orchestrator only coordinates
Он не должен генерировать final image prompt строкой внутри метода.

## 12.2. Нужна двухслойная схема
1. `Reasoning layer` → строит structured fashion brief.
2. `Prompt compiler` → превращает brief в generation payload.

## 12.3. Почему это полезно
- проще тестировать;
- можно валидировать structured brief;
- можно менять LLM или image backend;
- снижается связность.

---

# 13. Работа с fallback

## 13.1. Problem
Если vLLM недоступен, система не должна вести себя непредсказуемо.

## 13.2. Architecture
Fallback не должен быть "секретной веткой".  
Нужна отдельная стратегия:
- `PrimaryReasonerStrategy`
- `FallbackReasonerStrategy`

И orchestrator должен явно знать:
- какой provider использован;
- какой `DecisionResult` получен;
- была ли деградация качества.

## 13.3. Required telemetry
В `DecisionResult.telemetry`:
- `provider`
- `fallback_used`
- `reasoning_mode`
- `knowledge_items_count`
- `style_history_used`

---

# 14. Persistence strategy

## 14.1. Когда сохранять состояние
Контекст нужно сохранять:
1. после state transition;
2. до запуска generation job;
3. после создания job;
4. после recoverable error.

## 14.2. Почему
Это предотвращает:
- двойные generation jobs;
- потерю `flow_state`;
- повторный старт сценария;
- рассинхрон frontend/backend.

## 14.3. Transaction boundary
Желательно:
- state update + generation enqueue либо в одной транзакционной логике, либо через outbox pattern.

Для начального этапа допустим:
- save state → enqueue → save job id
но с idempotency key.

---

# 15. Idempotency и устойчивость

## 15.1. Почему нужна идемпотентность
Пользователь может:
- нажать кнопку дважды;
- обновить страницу;
- повторно отправить сообщение;
- словить retry на уровне сети.

## 15.2. Что нужно
- `client_message_id`
- `command_id`
- deduplication layer
- idempotency key для generation enqueue

## 15.3. Где это должно жить
В application layer и infrastructure queue adapter, а не в route и не в UI.

---

# 16. Observability by design

План проекта требует добавить сквозное логирование и метрики, потому что без этого система слишком сложна для дебага. citeturn153082view0

Orchestrator — центральная точка наблюдаемости.

## 16.1. Что логировать
На каждый вызов:
- `session_id`
- `message_id`
- `requested_intent`
- `resolved_mode`
- `flow_state_before`
- `flow_state_after`
- `decision_type`
- `clarification_kind`
- `provider`
- `knowledge_used`
- `generation_job_id`
- `style_id`
- `fallback_used`

## 16.2. Что мерить
- доля `clarification_required` по режимам;
- доля `text_and_generate`;
- доля recoverable errors;
- среднее число уточнений до generation;
- latency orchestration;
- queue enqueue success rate.

---

# 17. Testability

## 17.1. Что должно тестироваться unit-тестами
- mode resolver;
- state machine transitions;
- handler logic;
- `DecisionResult` mapping;
- anti-repeat constraint builder;
- occasion slot completeness.

## 17.2. Что должно тестироваться integration-тестами
- orchestrator + context store;
- orchestrator + mock reasoner;
- orchestrator + mock scheduler;
- orchestrator + prompt builder.

## 17.3. Что должно тестироваться e2e
- `garment_matching` start → follow-up → generation;
- `style_exploration` repeat with history;
- `occasion_outfit` clarification → generation;
- recoverable fallback path.

---

# 18. Recommended module layout

```text
application/stylist_chat/
  orchestrator/
    stylist_chat_orchestrator.py
    mode_router.py
    command_dispatcher.py
  handlers/
    general_advice_handler.py
    garment_matching_handler.py
    style_exploration_handler.py
    occasion_outfit_handler.py
  results/
    decision_result.py
  services/
    reasoning_context_builder.py
    diversity_constraints_builder.py
    clarification_message_builder.py
    generation_request_builder.py
  contracts/
    command.py
    response.py
```

---

# 19. Что не надо делать на этом этапе

Чтобы не сломать проект архитектурно, на Этапе 3 не надо:
- засовывать orchestrator прямо в route;
- держать mode-specific branching внутри одного `if/elif` на сотни строк;
- вызывать ComfyUI прямо из mode handler без scheduler abstraction;
- смешивать persistence и reasoning в одном сервисе;
- хранить anti-repeat как ad hoc список строк в route;
- делать LLM результат единственным источником истины;
- пытаться "починить" тишину через фронтовые костыли.

---

# 20. Пошаговый план реализации Этапа 3

## Подэтап 3.1. Ввести `DecisionResult`
Создать типизированную модель результата и перевести все ветки на неё.

## Подэтап 3.2. Создать `StylistChatOrchestrator`
Сделать единый application service, который принимает command и возвращает `DecisionResult`.

## Подэтап 3.3. Вынести mode handlers
Разделить логику по 4 режимам.

## Подэтап 3.4. Ввести builder’ы orchestration context
Разделить:
- reasoning context builder
- clarification builder
- generation request builder
- diversity constraints builder

## Подэтап 3.5. Вынести enqueue generation через scheduler abstraction
Никаких прямых вызовов image backend из route/handler.

## Подэтап 3.6. Встроить observability
Логи, telemetry, correlation ids.

## Подэтап 3.7. Добавить unit/integration tests
Покрыть сценарии и регрессии.

---

# 21. Критерии готовности этапа

Этап 3 считается реализованным корректно, если:

1. Между API route и LLM/generation stack есть отдельный orchestrator.
2. Все mode-specific сценарии вынесены в handlers.
3. Любой путь завершает работу типизированным `DecisionResult`.
4. Silent failure исчезает как класс, потому что отсутствует "неявный исход".
5. Generation создаётся только через scheduler abstraction.
6. Clarification — это формальный исход orchestrator, а не случайный текст.
7. Anti-repeat и style history проходят через orchestrator, а не теряются между сервисами.
8. Логи и telemetry позволяют восстановить путь решения по каждому сообщению.
9. Новую команду можно добавить без переписывания всей decision логики.
10. Код orchestration можно тестировать без реального vLLM и ComfyUI.

---

# 22. Архитектурный итог этапа

После Этапа 3 проект должен перейти:
- от "LLM-сервиса с кучей условий"
- к полноценному orchestration layer.

Именно этот шаг делает систему по-настоящему поддерживаемой:
- backend становится предсказуемым;
- сценарии — формализованными;
- генерация — управляемой;
- reasoning — заменяемым;
- knowledge layer — подключаемым;
- логика — тестируемой;
- рост проекта — нехаотичным.

Это центральный этап, который делает возможными все последующие шаги:
- полноценный `garment_matching`;
- slot-filling для `occasion_outfit`;
- anti-repeat для `style_exploration`;
- двухслойный prompt builder;
- knowledge-driven reasoning;
- обязательные generation jobs;
- наблюдаемость и эксплуатационную устойчивость.
