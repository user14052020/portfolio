
# Этап 4. Исправить «Подобрать к вещи» как полноценный сценарий

## Контекст этапа

В архитектурном плане проекта Этап 4 сформулирован как превращение команды **«Подобрать к вещи»** из частично неявного чата в полноценный управляемый сценарий. В плане явно зафиксировано, что после нажатия кнопки бот должен переводить сессию в состояние ожидания описания вещи, таймаут 60 секунд не должен завершать сценарий, после ответа пользователя должен формироваться `anchor_garment`, при нехватке данных задаётся одно короткое уточнение, а при достаточном `anchor_garment` система **обязана** перейти к generation job. 

Этот этап опирается на:
- **Этап 1** — доменная модель и state machine;
- **Этап 2** — тонкий frontend;
- **Этап 3** — explicit orchestrator и `DecisionResult`.

---

# 1. Цель этапа

Превратить сценарий `garment_matching` в отдельный устойчивый mode flow, в котором:

- команда запускается явно;
- follow-up не теряется;
- вещь нормализуется в структурированный объект;
- уточнения формализованы;
- generation является обязательным финалом режима;
- текстовые советы и image generation опираются на один structured outfit brief;
- сценарий масштабируется и тестируется как отдельный продуктовый use case.

---

# 2. Архитектурная проблема текущей реализации

Симптом из плана проекта: пользователь описывает вещь, бот что-то отвечает текстом, но generation не происходит. Это означает, что путь `command → follow-up → structured garment → generation` сейчас архитектурно не гарантирован. 

Типовые причины такого поведения:
1. команда не живёт как отдельный stateful flow;
2. follow-up интерпретируется как общий чат;
3. `anchor_garment` не выделяется как доменная сущность;
4. orchestrator не имеет жёсткого инварианта “достаточный garment → generation”;
5. уточнение сделано как LLM-текст, а не как formal clarification state;
6. frontend и backend по-разному понимают стадию сценария;
7. generation остаётся опциональным side effect вместо обязательного завершения режима.

Этап 4 устраняет это архитектурно, а не через точечные if/else.

---

# 3. Архитектурные принципы реализации

## 3.1. Clean Architecture

### Domain layer
Содержит:
- `AnchorGarment`
- `GarmentMatchingState`
- `GarmentMatchingPolicy`
- `GarmentCompletenessRules`
- `GarmentClarificationRules`

### Application layer
Содержит:
- `GarmentMatchingHandler`
- `StartGarmentMatchingUseCase`
- `ContinueGarmentMatchingUseCase`
- `BuildGarmentOutfitBriefUseCase`
- orchestration generation trigger

### Infrastructure layer
Содержит:
- garment extraction adapters;
- LLM reasoning adapters;
- style retrieval adapters;
- generation queue adapters;
- persistence adapters.

### Interface layer
Содержит:
- API contracts;
- DTO serializers;
- frontend command payload;
- response mappers.

## 3.2. SOLID

### Single Responsibility
- extractor отвечает только за извлечение `AnchorGarment`;
- clarifier — только за определение недостающих полей;
- handler — только за сценарий `garment_matching`;
- prompt builder — только за image/fashion brief compilation.

### Open/Closed
Добавление новых полей у вещи или новых источников данных не должно ломать flow.

### Liskov
`GarmentMatchingHandler` должен быть совместим с общим интерфейсом mode handlers.

### Interface Segregation
Не должно быть одного жирного сервиса “stylist everything”.
Нужны отдельные интерфейсы:
- `GarmentExtractor`
- `GarmentCompletenessEvaluator`
- `GarmentKnowledgeProvider`
- `OutfitBriefBuilder`
- `GenerationJobScheduler`

### Dependency Inversion
Handler зависит от интерфейсов, а не от конкретных vLLM/DB/queue реализаций.

## 3.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    garment_matching/
      entities/
      enums/
      policies/
      value_objects/
  application/
    stylist_chat/
      handlers/
        garment_matching_handler.py
      use_cases/
        start_garment_matching.py
        continue_garment_matching.py
        build_garment_outfit_brief.py
      services/
        garment_extraction_service.py
        garment_clarification_service.py
        garment_matching_context_builder.py
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
    garment/
    command/
    generation-job/
  features/
    run-garment-matching-command/
    send-garment-followup/
    attach-garment-asset/
  widgets/
    garment-matching-entry/
    garment-matching-followup/
    garment-generation-status/
  processes/
    stylist-chat/
```

---

# 4. Доменная модель режима `garment_matching`

## 4.1. Главная сущность: AnchorGarment

`AnchorGarment` — это не сырая строка пользователя, а нормализованное представление вещи, вокруг которой строится образ.

### Рекомендуемая модель

```python
class AnchorGarment(BaseModel):
    raw_user_text: str
    garment_type: str | None = None
    category: str | None = None
    color_primary: str | None = None
    color_secondary: list[str] = []
    material: str | None = None
    fit: str | None = None
    silhouette: str | None = None
    pattern: str | None = None
    seasonality: list[str] = []
    formality: str | None = None
    gender_context: str | None = None
    style_hints: list[str] = []
    asset_id: str | None = None
    confidence: float = 0.0
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False
```

## 4.2. Почему это важно
Без `AnchorGarment` система не может:
- валидно понять, хватает ли данных;
- адресно задавать уточнение;
- строить outfit brief;
- использовать retrieval по knowledge base;
- обеспечить anti-drift сценария.

---

# 5. State machine режима

## 5.1. Основные состояния

Режим `garment_matching` должен иметь собственный жизненный цикл:

- `idle`
- `awaiting_anchor_garment`
- `awaiting_anchor_garment_clarification`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`
- `recoverable_error`

## 5.2. Базовый путь

```text
START_COMMAND
→ awaiting_anchor_garment
→ receive_user_description
→ extract_anchor_garment
→ [if incomplete] clarification
→ [if sufficient] build_outfit_brief
→ ready_for_generation
→ generation_queued
→ completed
```

## 5.3. Главный инвариант
Если режим = `garment_matching` и `anchor_garment.is_sufficient_for_generation == True`,
то orchestrator **обязан** перейти в generation path.  
Ветки “дать совет текстом и не генерировать” по умолчанию быть не должно. 

---

# 6. Формализация входа в сценарий

## 6.1. Команда запуска

После нажатия quick action frontend должен отправлять command payload:

```json
{
  "session_id": "string",
  "requested_intent": "garment_matching",
  "command_name": "garment_matching",
  "command_step": "start",
  "message": null,
  "asset_id": null
}
```

## 6.2. Поведение orchestrator
На `command_step=start` orchestrator обязан:
1. загрузить/создать `ChatModeContext`;
2. установить:
   - `active_mode = garment_matching`
   - `flow_state = awaiting_anchor_garment`
   - `pending_clarification = true`
   - `clarification_kind = anchor_garment_description`
   - `should_auto_generate = true`
3. отправить служебное сообщение:
   - “Опиши вещь, к которой нужно подобрать образ”.

## 6.3. Таймаут 60 секунд
Архитектурное правило:
- таймаут 60 секунд **не имеет права завершать сценарий**;
- inactivity timeout может существовать только как технический TTL state cleanup, а не как бизнес-переход;
- `garment_matching` остаётся активным до:
  - завершения generation;
  - явной отмены;
  - системного recoverable/hard error.

Это прямое требование плана. 

---

# 7. Обработка follow-up пользователя

## 7.1. Follow-up — это не новый чат
После входа в режим следующее сообщение пользователя должно:
- идти в `ContinueGarmentMatchingUseCase`;
- не попадать в `general_advice`;
- не переопределяться свободным intent-классификатором.

## 7.2. Pipeline follow-up
1. Получить `ChatModeContext`.
2. Убедиться, что `active_mode == garment_matching`.
3. Считать сообщение кандидатом на описание вещи.
4. Передать его в `GarmentExtractor`.
5. Обновить `AnchorGarment`.
6. Проверить полноту.
7. Либо вернуть уточнение, либо идти к generation.

---

# 8. GarmentExtractor

## 8.1. Задача
Извлечь из текста пользователя структурированную вещь.

## 8.2. Источники входа
Extractor должен уметь работать с:
- текстом пользователя;
- metadata asset, если есть;
- conversation context;
- style hints из user profile, если это допустимо.

## 8.3. Архитектурный контракт

```python
class GarmentExtractor(Protocol):
    async def extract(
        self,
        user_text: str,
        asset_id: str | None = None,
        existing_anchor: AnchorGarment | None = None,
    ) -> AnchorGarment:
        ...
```

## 8.4. Правила
- extractor не создаёт generation job;
- extractor не пишет в БД напрямую;
- extractor возвращает только доменный объект;
- extractor может быть rule-based, LLM-based или hybrid;
- orchestrator не должен зависеть от конкретной реализации.

---

# 9. Оценка полноты и уточнения

## 9.1. GarmentCompletenessPolicy

Нужен отдельный policy service, который отвечает:
- достаточно ли данных для генерации;
- чего не хватает;
- какое уточнение задать.

### Минимальные обязательные поля
Для большинства случаев generation должны считаться достаточными хотя бы:
- `garment_type`
- `color_primary` или `material`
- `formality` или `seasonality` или `style_hints`

Это не значит, что все поля всегда обязательны.  
Правило должно быть гибким и расширяемым.

## 9.2. Почему нельзя делать это внутри LLM текста
Потому что тогда:
- невозможно жёстко контролировать сценарий;
- сложно тестировать completeness;
- трудно логировать, каких данных не хватило;
- поведение деградирует при смене модели.

## 9.3. Clarification policy
Если данных не хватает, бот задаёт **одно короткое уточнение**, а не общий стилистический ответ. Это тоже прямое требование плана. 

### Примеры:
- “Какого она цвета?”
- “Это более повседневная или более нарядная вещь?”
- “Из какого она материала?”

### Запрещено:
- длинный философский ответ;
- новое свободное рассуждение;
- несколько уточнений в одном длинном абзаце;
- уход в general advice.

---

# 10. Asset как дополнительный input, а не gatekeeper

План прямо фиксирует, что `garment_matching` не должен зависеть от обязательного наличия asset. 

## 10.1. Правильная роль asset
Asset:
- повышает confidence;
- помогает уточнить цвет/материал/тип;
- может выступать дополнительным evidence.

Но:
- отсутствие изображения не запрещает режим;
- asset не должен определять сам факт входа в сценарий.

## 10.2. Архитектурное правило
`AnchorGarment` может быть валиден:
- только по тексту;
- по тексту + asset;
- по asset + краткому тексту.

---

# 11. Построение outfit brief

## 11.1. После достаточного `AnchorGarment`
Если вещь нормализована и данных хватает, orchestrator должен построить `GarmentMatchingOutfitBrief`.

### Рекомендуемая модель

```python
class GarmentMatchingOutfitBrief(BaseModel):
    anchor_garment: AnchorGarment
    styling_goal: str
    harmony_rules: list[str]
    color_logic: list[str]
    silhouette_balance: list[str]
    complementary_garments: list[str]
    footwear_options: list[str]
    accessories: list[str]
    negative_constraints: list[str]
    historical_reference: list[str]
    tailoring_notes: list[str]
    image_prompt_notes: list[str]
```

## 11.2. Источники для brief
Brief должен строиться из:
- `AnchorGarment`
- style knowledge base
- color theory rules
- tailoring rules
- seasonality / formality logic
- user profile context
- optional retrieved related styles

## 11.3. Двухслойная схема
Как и в других режимах:
1. **Fashion reasoning layer** строит structured brief;
2. **Image prompt compiler** превращает его в generation payload.

---

# 12. Generation как обязательный финал режима

## 12.1. Жёсткое архитектурное правило
Если:
- режим = `garment_matching`
- `anchor_garment.is_sufficient_for_generation == True`

то система **всегда** должна:
- перейти к `ready_for_generation`
- создать generation job
- вернуть `DecisionResult.text_and_generate` или `generation_only`

Это центральное требование этапа. 

## 12.2. Почему нельзя оставлять текст без generation
Потому что тогда:
- UX сценария ломается;
- frontend и пользователь получают ложное завершение;
- логика команды не отличается от обычного чата;
- система перестаёт быть предсказуемой.

## 12.3. GenerationJobScheduler
Нужна абстракция:

```python
class GenerationJobScheduler(Protocol):
    async def enqueue(self, payload: dict) -> str:
        ...
```

`GarmentMatchingHandler` не должен вызывать ComfyUI напрямую.

---

# 13. Что должен делать GarmentMatchingHandler

## 13.1. Основной контракт

```python
class GarmentMatchingHandler(ChatModeHandler):
    async def handle(
        self,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        ...
```

## 13.2. Ответственность handler
Он должен:
- обрабатывать start команды;
- обрабатывать follow-up;
- использовать `GarmentExtractor`;
- применять completeness policy;
- вызывать clarification policy;
- строить outfit brief;
- запускать generation через scheduler;
- обновлять state;
- возвращать `DecisionResult`.

## 13.3. Что handler не должен делать
- писать SQL руками;
- делать raw HTTP вызовы в image backend;
- заниматься low-level логированием запросов;
- сам составлять final response DTO;
- смешивать бизнес-правила и транспорт.

---

# 14. Role of knowledge layer

## 14.1. Почему garment matching не должен быть только “подбором по вкусу модели”
Чтобы бот работал как:
- стилист;
- практик-портной;
- консультант по цвету,

нужно опираться на:
- palette logic;
- silhouette balancing;
- garment compatibility;
- fabric coherence;
- formality coherence;
- style references.

## 14.2. Что retrieval должен давать
Для `garment_matching` полезно доставать:
- compatible style directions;
- color pairing notes;
- tailoring balance notes;
- fabric compatibility notes;
- footwear/accessories heuristics;
- anti-clash constraints.

## 14.3. Контракт
```python
class GarmentKnowledgeProvider(Protocol):
    async def fetch_for_anchor_garment(
        self,
        garment: AnchorGarment,
        context: dict | None = None,
    ) -> dict:
        ...
```

---

# 15. Frontend после исправления сценария

## 15.1. Quick action
Frontend лишь запускает команду.

## 15.2. Follow-up input
После служебного сообщения UI должен:
- показать placeholder вида “Например: тёмно-синяя джинсовая рубашка oversize”;
- не сбрасывать сценарий через локальные таймауты;
- отправить follow-up как обычное сообщение в ту же сессию.

## 15.3. Async generation UX
После `text_and_generate` frontend:
1. рендерит текст;
2. показывает pending image block;
3. подписывается на `job_id`;
4. подставляет картинку по готовности.

Frontend не должен угадывать, завершён ли сценарий.

---

# 16. Persistence и устойчивость

## 16.1. Что должно храниться в session state
Минимум:
- `active_mode`
- `flow_state`
- `pending_clarification`
- `clarification_kind`
- `anchor_garment`
- `current_job_id`
- `last_decision_type`
- `updated_at`

## 16.2. Когда сохранять
1. После входа в режим;
2. После извлечения/обновления `AnchorGarment`;
3. После определения clarification;
4. До enqueue generation;
5. После получения `job_id`.

## 16.3. Idempotency
Нужны:
- `client_message_id`
- dedupe на follow-up messages
- generation enqueue idempotency key

Это защищает от:
- двойных кликов;
- повторной отправки follow-up;
- дублей generation jobs.

---

# 17. Observability

## 17.1. Что логировать
На каждый шаг сценария:
- `session_id`
- `message_id`
- `active_mode`
- `flow_state_before`
- `flow_state_after`
- `clarification_kind`
- `anchor_garment_confidence`
- `anchor_garment_completeness`
- `decision_type`
- `generation_job_id`
- `knowledge_provider_used`
- `provider`
- `fallback_used`

## 17.2. Метрики режима
- `% garment_matching flows ending in generation`
- среднее число уточнений до generation
- доля incomplete garment
- доля flows, завершённых без изображения
- доля recoverable errors
- average extraction confidence

Это нужно, чтобы видеть, где сценарий ломается:
- extraction;
- completeness;
- reasoning;
- queue;
- generation backend.

---

# 18. Тестирование

## 18.1. Unit tests
Покрыть:
- `GarmentExtractor` adapters
- completeness policy
- clarification builder
- state machine transitions
- `GarmentMatchingHandler` branches
- required generation invariant

## 18.2. Integration tests
Покрыть:
- start command → clarification
- follow-up with sufficient garment → generation job
- follow-up with insufficient garment → one clarification
- text + asset path
- text-only path without asset

## 18.3. E2E сценарии
Минимальный набор:
1. “Подобрать к вещи” → “чёрная кожаная куртка” → generation
2. “Подобрать к вещи” → “рубашка” → уточнение → “белая льняная” → generation
3. вход с asset без текста → уточнение → generation
4. двойная отправка follow-up → один job
5. recoverable failure queue → graceful response

---

# 19. Рекомендуемая модульная структура

```text
domain/garment_matching/
  entities/
    anchor_garment.py
    garment_matching_outfit_brief.py
  policies/
    garment_completeness_policy.py
    garment_clarification_policy.py
  enums/
    garment_flow_state.py

application/stylist_chat/handlers/
  garment_matching_handler.py

application/stylist_chat/use_cases/
  start_garment_matching.py
  continue_garment_matching.py
  build_garment_outfit_brief.py

application/stylist_chat/services/
  garment_extraction_service.py
  garment_matching_context_builder.py
  garment_brief_compiler.py

infrastructure/llm/
  llm_garment_extractor.py
  llm_garment_reasoner.py

infrastructure/knowledge/
  garment_knowledge_provider.py

infrastructure/queue/
  generation_job_scheduler.py
```

---

# 20. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- пытаться чинить режим фронтовыми таймерами;
- делать generation как побочный if в route;
- решать полноту вещи только в LLM ответе;
- отправлять `garment_matching` обратно в `general_advice` при любой неоднозначности;
- жёстко завязывать режим на asset;
- смешивать extraction, reasoning и generation в одном методе;
- лечить баги “проверками на всякий случай” без domain contracts.

---

# 21. Пошаговый план реализации Этапа 4

## Подэтап 4.1. Ввести `AnchorGarment`
Создать доменную сущность и контракты сериализации.

## Подэтап 4.2. Реализовать `GarmentMatching` state machine
Зафиксировать переходы:
- start
- awaiting description
- clarification
- ready
- generate
- done

## Подэтап 4.3. Реализовать `GarmentExtractor`
Сделать интерфейс + первую реализацию.

## Подэтап 4.4. Реализовать completeness / clarification policies
Вынести полноту и уточнения в отдельные policy services.

## Подэтап 4.5. Реализовать `GarmentMatchingHandler`
Подключить в orchestrator.

## Подэтап 4.6. Реализовать outfit brief builder
Построение structured brief из garment + knowledge.

## Подэтап 4.7. Обязательная generation path
Подключить scheduler и сделать generation неизбежным финалом достаточного сценария.

## Подэтап 4.8. Добавить observability и тесты
Сделать режим прозрачным для диагностики.

---

# 22. Критерии готовности этапа

Этап 4 реализован корректно, если:

1. Команда `garment_matching` живёт как отдельный сценарий, а не как обычный чат.
2. После quick action сессия переходит в `awaiting_anchor_garment`.
3. Таймаут 60 секунд не завершает сценарий бизнес-логически.
4. Follow-up не уходит в `general_advice`.
5. `AnchorGarment` нормализуется в отдельную сущность.
6. При неполных данных задаётся одно короткое уточнение.
7. При достаточном garment generation всегда создаётся.
8. Frontend получает `job_id` и async-статус.
9. Режим покрыт unit / integration / e2e тестами.
10. Код сценария можно развивать отдельно от других режимов.

---

# 23. Архитектурный итог этапа

После реализации Этапа 4 команда **«Подобрать к вещи»** перестаёт быть случайным поведением в общем чате и становится полноценным продуктовым flow:

- с ясной доменной моделью;
- с отдельным state machine;
- с устойчивым follow-up;
- с формализованным `AnchorGarment`;
- с retrieval/knowledge support;
- с обязательной generation job;
- с прозрачной диагностикой;
- с высокой поддерживаемостью.

Именно после такого изменения режим можно масштабировать дальше:
- добавлять vision extraction;
- дообогащать style knowledge;
- улучшать tailoring logic;
- подключать ranking вариантов;
- сохранять и переиспользовать outfit briefs;
- анализировать качество как отдельный сценарий продукта.
