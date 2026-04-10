
# Этап 5. Исправить «Что надеть на событие» как slot-filling flow

## Контекст этапа

В архитектурном плане проекта Этап 5 сформулирован как перевод команды **«Что надеть на событие»** из неустойчивого диалога в **slot-filling flow**. В самом плане зафиксировано:
- нужен отдельный `occasion_context`;
- минимальные слоты: `event_type`, `location`, `time_of_day`, `season`, `dress_code`, `weather_context`, `desired_impression`;
- уточнения должны идти **по слотам**, а не как общий свободный разговор;
- если достаточный контекст уже собран, система не должна снова спрашивать или замолкать, а должна переходить к generation. citeturn108346view0

Этот этап опирается на:
- **Этап 1** — доменная модель, `ChatModeContext`, state machines;
- **Этап 2** — тонкий frontend;
- **Этап 3** — explicit orchestrator и `DecisionResult`;
- **Этап 4** — опыт построения полноценного сценарного flow на примере `garment_matching`.

---

# 1. Цель этапа

Сделать режим `occasion_outfit` самостоятельным, управляемым и тестируемым сценарием, в котором:

- вход в сценарий запускается явно;
- follow-up пользователя всегда интерпретируется как продолжение сценария;
- контекст события хранится как структурированная сущность;
- уточнения заполняют конкретные недостающие слоты;
- при достижении минимального достаточного контекста generation становится обязательным следующим шагом;
- reasoning и image prompt строятся на основе `OccasionContext`, а не случайной интерпретации одного последнего сообщения;
- сценарий остаётся поддерживаемым и расширяемым.

---

# 2. Архитектурная проблема текущей реализации

Симптом из плана: бот задаёт уточнение, пользователь конкретизирует, после чего наступает тишина вместо генерации. Это означает, что сценарий мероприятия сейчас **не формализован как slot-filling pipeline** и не имеет жёсткого перехода:
`clarification answered -> context sufficient -> generation`. citeturn108346view0

Типовые причины:
1. нет отдельной сущности `OccasionContext`;
2. follow-up после уточнения обрабатывается как новый свободный чат;
3. полнота контекста определяется неявно и непредсказуемо;
4. orchestrator не знает, что scenario readiness уже достигнут;
5. нет formal clarification contract;
6. generation остаётся опциональным или теряется между сервисами;
7. frontend/backend расходятся в понимании стадии сценария.

Этап 5 устраняет именно эти причины, а не лечит симптом точечными ветками.

---

# 3. Архитектурные принципы реализации

## 3.1. Clean Architecture

### Domain layer
Содержит:
- `OccasionContext`
- `OccasionSlot`
- `OccasionFlowState`
- `OccasionCompletenessPolicy`
- `OccasionClarificationPolicy`
- `OccasionOutfitBrief`

### Application layer
Содержит:
- `OccasionOutfitHandler`
- `StartOccasionOutfitUseCase`
- `ContinueOccasionOutfitUseCase`
- `UpdateOccasionContextUseCase`
- `BuildOccasionOutfitBriefUseCase`
- orchestrated generation trigger

### Infrastructure layer
Содержит:
- LLM adapters;
- occasion extraction adapters;
- style knowledge retrieval adapters;
- queue / generation scheduler;
- persistence adapters.

### Interface layer
Содержит:
- API contracts;
- request/response DTO;
- frontend command payload;
- serializers.

## 3.2. SOLID

### Single Responsibility
- extractor отвечает только за извлечение slot data;
- completeness policy — только за определение достаточности контекста;
- clarification policy — только за выбор следующего уточнения;
- handler — только за сценарий `occasion_outfit`;
- brief builder — только за построение структурированного outfit brief.

### Open/Closed
Добавление нового слота или новой retrieval-логики не должно требовать переписывать orchestrator целиком.

### Liskov
`OccasionOutfitHandler` должен быть совместим с общим контрактом mode handlers.

### Interface Segregation
Вместо одного общего “stylist super service” нужны отдельные интерфейсы:
- `OccasionContextExtractor`
- `OccasionCompletenessEvaluator`
- `OccasionClarificationSelector`
- `OccasionKnowledgeProvider`
- `OccasionOutfitBriefBuilder`
- `GenerationJobScheduler`

### Dependency Inversion
Application layer зависит от абстракций, а не от конкретных реализаций vLLM, Redis, ComfyUI и БД.

## 3.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    occasion_outfit/
      entities/
      enums/
      policies/
      value_objects/
  application/
    stylist_chat/
      handlers/
        occasion_outfit_handler.py
      use_cases/
        start_occasion_outfit.py
        continue_occasion_outfit.py
        update_occasion_context.py
        build_occasion_outfit_brief.py
      services/
        occasion_extraction_service.py
        occasion_clarification_service.py
        occasion_context_builder.py
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
    occasion/
    command/
    generation-job/
  features/
    run-occasion-command/
    send-occasion-followup/
  widgets/
    occasion-entry/
    occasion-followup/
    occasion-generation-status/
  processes/
    stylist-chat/
```

---

# 4. Доменная модель режима `occasion_outfit`

## 4.1. Главная сущность: OccasionContext

`OccasionContext` — это структурированное описание события и запроса пользователя, вокруг которого строится образ.

### Рекомендуемая модель

```python
class OccasionContext(BaseModel):
    raw_user_texts: list[str] = []
    event_type: str | None = None
    location: str | None = None
    time_of_day: str | None = None
    season: str | None = None
    dress_code: str | None = None
    weather_context: str | None = None
    desired_impression: str | None = None
    constraints: list[str] = []
    color_preferences: list[str] = []
    garment_preferences: list[str] = []
    comfort_requirements: list[str] = []
    confidence: float = 0.0
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False
```

## 4.2. Почему это важно
Без `OccasionContext` система:
- не знает, каких данных не хватает;
- не умеет задавать slot-specific уточнение;
- не может объяснимо перейти к generation;
- не может строить narrative/reasoning вокруг события;
- не может использовать occasion-specific knowledge retrieval.

---

# 5. Slot model

## 5.1. Обязательные и опциональные слоты

Из плана следует, что в модели должны существовать по меньшей мере следующие слоты: `event_type`, `location`, `time_of_day`, `season`, `dress_code`, `weather_context`, `desired_impression`. citeturn108346view0

### Базовая классификация

#### Core slots
- `event_type`
- `time_of_day`
- `season`

#### Styling slots
- `dress_code`
- `desired_impression`

#### Environment slots
- `location`
- `weather_context`

#### Optional enrichments
- `constraints`
- `color_preferences`
- `garment_preferences`
- `comfort_requirements`

## 5.2. Минимальный достаточный набор
Архитектурно рекомендуется считать сценарий **готовым к generation**, если заполнены:

- `event_type`
- `time_of_day`
- `season`
- хотя бы один из:
  - `dress_code`
  - `desired_impression`

Все остальные слоты — усиливают результат, но не должны бесконечно задерживать generation.

---

# 6. State machine режима

## 6.1. Основные состояния

Режим `occasion_outfit` должен иметь собственный жизненный цикл:

- `idle`
- `awaiting_occasion_details`
- `awaiting_occasion_clarification`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`
- `recoverable_error`

## 6.2. Базовый путь

```text
START_COMMAND
→ awaiting_occasion_details
→ receive_user_details
→ extract_occasion_slots
→ [if incomplete] clarification
→ [if sufficient] build_outfit_brief
→ ready_for_generation
→ generation_queued
→ completed
```

## 6.3. Главный инвариант
Если режим = `occasion_outfit` и `occasion_context.is_sufficient_for_generation == True`,
то orchestrator **обязан** перейти в generation path.  
Ветки “задать ещё один общий вопрос” или “ничего не сделать” быть не должно.

---

# 7. Формализация входа в сценарий

## 7.1. Команда запуска

После нажатия quick action frontend должен отправлять command payload:

```json
{
  "session_id": "string",
  "requested_intent": "occasion_outfit",
  "command_name": "occasion_outfit",
  "command_step": "start",
  "message": null,
  "asset_id": null
}
```

## 7.2. Поведение orchestrator
На `command_step=start` orchestrator обязан:
1. загрузить/создать `ChatModeContext`;
2. установить:
   - `active_mode = occasion_outfit`
   - `flow_state = awaiting_occasion_details`
   - `pending_clarification = true`
   - `clarification_kind = occasion_missing_multiple_slots`
   - `should_auto_generate = true`
3. отправить стартовое сообщение-уточнение, например:
   - “Расскажи, что это за событие, в какое время и какое впечатление ты хочешь произвести”.

## 7.3. Таймаут 60 секунд
Как и в `garment_matching`, таймаут 60 секунд не должен завершать сценарий бизнес-логически. Это прямо задано в плане. citeturn108346view0

Архитектурное правило:
- inactivity timeout допустим только как технический cleanup старых state;
- `occasion_outfit` остаётся активным до завершения generation, отмены или recoverable/hard error.

---

# 8. Follow-up пользователя как slot update, а не новый чат

## 8.1. Ключевой принцип
После старта сценария следующее сообщение пользователя не должно снова идти в `general_advice` или свободную intent-классификацию.

## 8.2. Pipeline
1. Загрузить `ChatModeContext`.
2. Проверить `active_mode == occasion_outfit`.
3. Передать сообщение в `OccasionContextExtractor`.
4. Обновить `OccasionContext`.
5. Оценить completeness.
6. Либо выбрать следующий clarification, либо переходить к generation.

---

# 9. OccasionContextExtractor

## 9.1. Задача
Извлечь и обновить slot data по мероприятию на основе текста пользователя.

## 9.2. Архитектурный контракт

```python
class OccasionContextExtractor(Protocol):
    async def extract(
        self,
        user_text: str,
        existing_context: OccasionContext | None = None,
    ) -> OccasionContext:
        ...
```

## 9.3. Правила
- extractor не принимает решение о generation;
- extractor не пишет в БД;
- extractor только извлекает/обновляет доменную сущность;
- extractor может быть hybrid: rule-based + LLM-assisted;
- orchestrator не должен зависеть от конкретной реализации.

## 9.4. Что extractor должен уметь
- определять `event_type` из фраз вроде “свадьба”, “выставка”, “деловой ужин”;
- извлекать `time_of_day` (“вечером”, “утром”, “днём”);
- извлекать `season` или определять её из даты/контекста;
- выделять `dress_code` и `desired_impression`;
- при повторных сообщениях не терять уже собранные слоты.

---

# 10. Completeness policy

## 10.1. OccasionCompletenessPolicy
Нужен отдельный policy service, который отвечает:
- достаточно ли контекста для generation;
- какие слоты пусты;
- какой следующий слот спросить;
- не будет ли следующий вопрос лишним.

## 10.2. Почему нельзя оставлять это на усмотрение LLM ответа
Без формального policy:
- бот может бесконечно спрашивать;
- может считать достаточным слишком мало данных;
- может молчать после нужного ответа;
- поведение станет неустойчивым при смене модели.

## 10.3. Базовая логика
Если есть:
- `event_type`
- `time_of_day`
- `season`
- и хотя бы один из:
  - `dress_code`
  - `desired_impression`

то `OccasionContext.is_sufficient_for_generation = True`.

---

# 11. Clarification policy

## 11.1. Принцип
Уточнения должны идти **по слотам**, а не в свободной форме. Это прямо зафиксировано в плане. citeturn108346view0

## 11.2. OccasionClarificationSelector
Нужен отдельный сервис, который выбирает **один лучший следующий вопрос**.

### Пример контракта

```python
class OccasionClarificationSelector(Protocol):
    async def select_next(
        self,
        context: OccasionContext,
    ) -> tuple[str, str]:
        ...
```

Где возвращаются:
- `clarification_kind`
- `clarification_text`

## 11.3. Примеры уточнений
- если нет `event_type` → “Что это за событие?”
- если нет `time_of_day` → “Это днём или вечером?”
- если нет `season` → “Для какого времени года ты подбираешь образ?”
- если нет и `dress_code`, и `desired_impression` → “Это более формальное мероприятие или ты хочешь произвести какое-то конкретное впечатление?”

## 11.4. Запрещено
- задавать несколько длинных уточнений в одном сообщении;
- возвращаться в общий стилистический разговор;
- спрашивать то, что уже заполнено;
- повторно спрашивать тот же слот без причины.

---

# 12. OccasionOutfitBrief

## 12.1. После достаточного контекста
Если `OccasionContext` достаточен, orchestrator должен строить `OccasionOutfitBrief`.

### Рекомендуемая модель

```python
class OccasionOutfitBrief(BaseModel):
    occasion_context: OccasionContext
    styling_goal: str
    dress_code_logic: list[str]
    impression_logic: list[str]
    color_logic: list[str]
    silhouette_logic: list[str]
    garment_recommendations: list[str]
    footwear_recommendations: list[str]
    accessories: list[str]
    outerwear_notes: list[str]
    comfort_notes: list[str]
    historical_reference: list[str]
    tailoring_notes: list[str]
    negative_constraints: list[str]
    image_prompt_notes: list[str]
```

## 12.2. Источники для brief
Brief должен строиться из:
- `OccasionContext`
- style knowledge base
- event-specific dressing heuristics
- color theory
- tailoring logic
- weather/season logic
- user profile context
- occasion-related style retrieval

## 12.3. Двухслойная схема
1. **Fashion reasoning layer** строит structured occasion brief;
2. **Image prompt compiler** переводит brief в generation payload.

---

# 13. Generation как обязательный финал режима

## 13.1. Жёсткое правило
Если `occasion_context.is_sufficient_for_generation == True`,
то orchestrator всегда должен:
- перейти к `ready_for_generation`;
- создать generation job;
- вернуть `DecisionResult.text_and_generate` или `generation_only`.

Это устраняет симптом “после уточнения — тишина”.

## 13.2. Почему это обязательно
Иначе UX режима ломается:
- пользователь выполняет просьбу системы;
- но не получает обещанный результат;
- сценарий становится непредсказуемым;
- backend теряет смысл как orchestrated flow.

## 13.3. GenerationJobScheduler
Нужна абстракция:

```python
class GenerationJobScheduler(Protocol):
    async def enqueue(self, payload: dict) -> str:
        ...
```

`OccasionOutfitHandler` не должен напрямую вызывать ComfyUI.

---

# 14. Что должен делать OccasionOutfitHandler

## 14.1. Основной контракт

```python
class OccasionOutfitHandler(ChatModeHandler):
    async def handle(
        self,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        ...
```

## 14.2. Ответственность handler
Он должен:
- обрабатывать start команды;
- обрабатывать follow-up;
- использовать `OccasionContextExtractor`;
- применять completeness policy;
- выбирать следующий clarification;
- строить occasion outfit brief;
- запускать generation через scheduler;
- обновлять state;
- возвращать `DecisionResult`.

## 14.3. Что handler не должен делать
- выполнять raw SQL;
- делать raw HTTP к image backend;
- смешивать slot extraction и response serialization;
- хранить крупную бизнес-логику в transport layer;
- принимать решения за frontend.

---

# 15. Knowledge layer для occasion flow

## 15.1. Почему этот режим не должен быть “чистой фантазией модели”
Чтобы бот отвечал как:
- стилист;
- практик-портной;
- консультант по уместности образа;
- человек, умеющий сочетать стиль, событие, цвет и впечатление,

нужно опираться на knowledge layer, а не на случайную память модели.

## 15.2. Что retrieval должен возвращать
Для `occasion_outfit` полезно доставать:
- occasion dressing rules;
- dress-code heuristics;
- style profiles, подходящие событию;
- weather-aware styling notes;
- tailoring and fit notes;
- color pairing rules;
- historical / cultural references, если уместно.

## 15.3. Контракт

```python
class OccasionKnowledgeProvider(Protocol):
    async def fetch_for_occasion(
        self,
        context: OccasionContext,
        profile_context: dict | None = None,
    ) -> dict:
        ...
```

---

# 16. Frontend после исправления сценария

## 16.1. Quick action
Frontend только инициирует команду.

## 16.2. Follow-up input
После стартового уточнения UI должен:
- показывать placeholder, связанный с событием;
- не сбрасывать сценарий локальным таймаутом;
- отправлять follow-up как обычное сообщение в ту же сессию.

Пример placeholder:
- “Например: вечерняя выставка современного искусства осенью, хочу выглядеть интеллектуально и немного смело”.

## 16.3. Async generation UX
После `text_and_generate` frontend:
1. рендерит текст;
2. показывает pending image block;
3. подписывается на `job_id`;
4. обновляет UI после завершения generation.

Frontend не должен сам решать, “хватило ли уже данных”.

---

# 17. Persistence и устойчивость

## 17.1. Что должно храниться в session state
Минимум:
- `active_mode`
- `flow_state`
- `pending_clarification`
- `clarification_kind`
- `occasion_context`
- `current_job_id`
- `last_decision_type`
- `updated_at`

## 17.2. Когда сохранять
1. После входа в режим;
2. После каждого обновления `OccasionContext`;
3. После выбора следующего clarification;
4. До enqueue generation;
5. После получения `job_id`.

## 17.3. Idempotency
Нужны:
- `client_message_id`
- dedupe follow-up messages
- idempotency key для generation enqueue

Это предотвращает:
- двойные уточнения;
- повторные generation jobs;
- рассинхрон frontend/backend.

---

# 18. Observability

## 18.1. Что логировать
На каждый шаг сценария:
- `session_id`
- `message_id`
- `active_mode`
- `flow_state_before`
- `flow_state_after`
- `clarification_kind`
- `filled_slots`
- `missing_slots`
- `occasion_completeness`
- `decision_type`
- `generation_job_id`
- `provider`
- `fallback_used`

## 18.2. Метрики режима
- `% occasion flows ending in generation`
- среднее число уточнений до generation
- доля silent failures
- доля flows, где недостаёт одного и того же слота
- average slot completeness by step
- generation success rate after readiness

Это позволит видеть, где ломается сценарий:
- extraction;
- clarification;
- completeness evaluation;
- queue;
- generation backend.

---

# 19. Тестирование

## 19.1. Unit tests
Покрыть:
- `OccasionContextExtractor`
- completeness policy
- clarification selector
- state machine transitions
- `OccasionOutfitHandler`
- required generation invariant

## 19.2. Integration tests
Покрыть:
- start command -> first clarification
- follow-up with insufficient slots -> second clarification
- follow-up with sufficient slots -> generation job
- repeated follow-up dedupe
- recoverable provider failure path

## 19.3. E2E сценарии
Минимальный набор:
1. “Что надеть на событие” → “дневная свадьба летом, хочу выглядеть элегантно” → generation
2. “Что надеть на событие” → “выставка” → уточнение → “вечером осенью, smart casual” → generation
3. недостаточно данных → один точный follow-up → generation
4. повторная отправка follow-up → один job
5. recoverable queue failure → корректный recoverable response

---

# 20. Рекомендуемая модульная структура

```text
domain/occasion_outfit/
  entities/
    occasion_context.py
    occasion_outfit_brief.py
  policies/
    occasion_completeness_policy.py
    occasion_clarification_policy.py
  enums/
    occasion_flow_state.py

application/stylist_chat/handlers/
  occasion_outfit_handler.py

application/stylist_chat/use_cases/
  start_occasion_outfit.py
  continue_occasion_outfit.py
  update_occasion_context.py
  build_occasion_outfit_brief.py

application/stylist_chat/services/
  occasion_extraction_service.py
  occasion_context_builder.py
  occasion_brief_compiler.py

infrastructure/llm/
  llm_occasion_extractor.py
  llm_occasion_reasoner.py

infrastructure/knowledge/
  occasion_knowledge_provider.py

infrastructure/queue/
  generation_job_scheduler.py
```

---

# 21. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- лечить режим фронтовыми таймерами;
- интерпретировать follow-up через общий intent-классификатор;
- определять completeness только из текста LLM ответа;
- задавать общие свободные вопросы вместо slot-specific;
- держать generation как опциональный side effect;
- смешивать extraction, reasoning и generation в одном методе;
- решать проблему “тишины” через случайные fallback-ветки без типизированного `DecisionResult`.

---

# 22. Пошаговый план реализации Этапа 5

## Подэтап 5.1. Ввести `OccasionContext`
Создать доменную сущность и контракты сериализации.

## Подэтап 5.2. Реализовать slot model и state machine
Зафиксировать:
- старт сценария;
- ожидание деталей;
- уточнение;
- готовность;
- generation;
- завершение.

## Подэтап 5.3. Реализовать `OccasionContextExtractor`
Сделать интерфейс и первую реализацию.

## Подэтап 5.4. Реализовать completeness / clarification policies
Отдельные policy services для заполненности и выбора следующего уточнения.

## Подэтап 5.5. Реализовать `OccasionOutfitHandler`
Подключить его в orchestrator.

## Подэтап 5.6. Реализовать occasion outfit brief builder
Построение structured brief из slots + knowledge.

## Подэтап 5.7. Обязательная generation path
Подключить scheduler и сделать generation неизбежным финалом готового сценария.

## Подэтап 5.8. Добавить observability и тесты
Сделать сценарий прозрачным и диагностируемым.

---

# 23. Критерии готовности этапа

Этап 5 реализован корректно, если:

1. Команда `occasion_outfit` живёт как отдельный slot-filling flow.
2. После quick action сессия переходит в `awaiting_occasion_details`.
3. Таймаут 60 секунд не завершает сценарий бизнес-логически.
4. Follow-up не уходит в `general_advice`.
5. `OccasionContext` нормализуется в отдельную сущность.
6. Уточнения выбираются по конкретным недостающим слотам.
7. При достаточном контексте generation всегда создаётся.
8. Frontend получает `job_id` и async-статус.
9. Режим покрыт unit / integration / e2e тестами.
10. Код сценария можно развивать отдельно от других режимов.

---

# 24. Архитектурный итог этапа

После реализации Этапа 5 команда **«Что надеть на событие»** перестаёт быть хрупкой беседой и становится полноценным slot-filling сценарным flow:

- с ясной доменной моделью;
- с отдельным state machine;
- с устойчивым follow-up;
- с формализованным `OccasionContext`;
- с slot-based clarification;
- с обязательной generation job;
- с retrieval/knowledge support;
- с прозрачной диагностикой;
- с высокой поддерживаемостью.

Именно после такого изменения режим можно масштабировать дальше:
- добавлять новые слоты;
- обогащать event-specific knowledge;
- улучшать dress-code reasoning;
- учитывать климат и географию;
- вводить ranking вариантов;
- сохранять и переиспользовать occasion briefs;
- анализировать качество как отдельный сценарий продукта.
