
# Этап 2. Routing redesign  
## Подробный план реализации semantic routing для fashion chatbot

## 0. Назначение документа

Этот документ выделяет и детализирует второй implementation block из общего master-плана переработки fashion chatbot. Его задача — описать, как должна быть перестроена система определения сценария и управления режимами диалога, чтобы уйти от слабого keyword-based routing к устойчивому **semantic routing через vLLM**, не разрушая при этом чистую архитектуру, разделение ответственности и будущую расширяемость системы. Общий master-план уже зафиксировал, что keyword routing должен остаться только fallback-механизмом, а основное определение mode должно делать отдельное routing-звено на vLLM. fileciteturn8file0

Этот документ фиксирует:
- зачем нужен routing redesign;
- почему текущего keyword routing недостаточно;
- как должен работать новый `ConversationRouter`;
- как разделить routing и reasoning;
- как изменится state machine;
- как должен быть устроен routing contract;
- как хранить и передавать контекст для роутинга;
- как реализовать fallback и graceful degradation;
- какие backend и frontend изменения для этого потребуются.

---

# 1. Контекст и проблема

## 1.1. Текущее состояние

После этапов 0–9 система уже имеет:
- базу стилей;
- orchestrator;
- prompt builder;
- generation pipeline;
- разделение reasoning и generation на верхнем уровне.

Но routing по-прежнему концептуально слабый. Из общего master-плана следует, что жёсткий mode detection по ключевым словам не подходит для fashion chatbot, потому что реальные пользовательские запросы слишком неоднозначны, богаты смыслом и часто не содержат очевидных триггерных слов. fileciteturn8file0

---

## 1.2. Почему keyword routing не годится как основной механизм

Keyword routing быстро ломается на сообщениях вроде:

- “Хочу что-то строгое на открытие выставки”
- “Есть серый жакет, но хочется более мягкий образ”
- “Собери что-нибудь в духе интеллектуального минимализма”
- “Не знаю, что надеть, чтобы было собранно, но не скучно”

Во всех этих примерах пользователь:
- не обязательно использует явные триггерные слова;
- может не называть сценарий напрямую;
- может совмещать просьбу о совете, визуализации, историческом стиле и вкусовом ориентире в одном сообщении.

Значит, mode detection должен опираться не на ключевые слова, а на **смысл сообщения и контекст диалога**.

---

## 1.3. Бизнес-симптомы слабого routing
Если оставить старую схему:
- бот будет ошибочно включать генерацию;
- режимы будут залипать;
- garment/occasion/general requests будут перемешиваться;
- придётся бесконечно расширять словари триггеров;
- новые knowledge layers и profile context не смогут надёжно подключаться к правильным сценариям.

Следовательно, routing redesign — это обязательный архитектурный этап, а не локальный refactor.

---

# 2. Цель этапа

После реализации routing redesign система должна работать по следующей схеме:

```text
user message
→ ConversationRouter (vLLM router call)
→ RoutingDecision
→ code retrieval / orchestration
→ FashionReasoner (second vLLM call)
→ response / brief / clarification / optional generation
```

Эта схема уже зафиксирована в master-плане и здесь становится полноценным архитектурным контрактом. fileciteturn8file0

---

# 3. Новый архитектурный принцип routing

## 3.1. Основное правило

### Rule 1
Keyword routing допустим только как fallback.

### Rule 2
Основной mode detection делает `ConversationRouter` через vLLM.

### Rule 3
Routing и reasoning — разные стадии и разные компоненты.

Эти правила не должны существовать как абстрактные пожелания. Они должны быть реализованы в виде:
- отдельных интерфейсов;
- отдельных application services;
- отдельного routing contract;
- отдельного response schema.

---

## 3.2. Что именно определяет routing

Routing должен отвечать не только на вопрос “какой mode”, но и на несколько дополнительных:

- это обычный совет или сценарий под конкретную задачу?
- нужен ли clarification step?
- пользователь просит просто поговорить или хочет визуализацию?
- есть ли активное продолжение старого flow?
- можно ли продолжать текущий mode или нужен reset?
- есть ли явный generation intent?

Таким образом routing должен возвращать не один enum, а полноценный decision object.

---

# 4. Новый компонент: `ConversationRouter`

## 4.1. Назначение

`ConversationRouter` — это отдельный application service, который:
- получает текущее сообщение пользователя;
- получает краткий session context;
- знает допустимые modes;
- вызывает vLLM в режиме короткого semantic classification;
- возвращает структурированный `RoutingDecision`.

---

## 4.2. Что `ConversationRouter` не делает

Он не должен:
- собирать prompt для картинки;
- делать retrieval из knowledge layer;
- генерировать ответ пользователю;
- выбирать конкретный garment set;
- формировать `FashionBrief`;
- запускать ComfyUI;
- писать в chat history финальный assistant response.

Эти обязанности принадлежат другим слоям системы.

---

## 4.3. Почему это важно
Это обеспечивает:
- SRP;
- тестируемость;
- возможность быстро заменить routing strategy;
- более простую отладку;
- чистое разделение между “понять сценарий” и “решить, что сказать”.

---

# 5. RoutingDecision как доменная сущность

## 5.1. Новый контракт

Routing должен возвращать структурированную сущность, а не магические значения в dict.

Рекомендуемая модель:

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
    notes: str | None
```

---

## 5.2. Что означают поля

### `mode`
Какой сценарий активируется:
- `general_advice`
- `style_exploration`
- `occasion_outfit`
- `garment_matching`
- `clarification_only`
- в будущем другие modes

### `confidence`
Насколько router уверен в решении.

### `needs_clarification`
Нужно ли сначала задать уточнение.

### `missing_slots`
Каких данных не хватает для продолжения сценария.

### `generation_intent`
Есть ли явный запрос на визуализацию.

### `continue_existing_flow`
Нужно ли продолжить текущий незавершённый сценарий.

### `should_reset_to_general`
Нужно ли сбросить stale mode и перейти в общий диалог.

### `reasoning_depth`
Подсказка для следующего этапа:
- `light`
- `normal`
- `deep`

---

# 6. Двухшаговый вызов vLLM

## 6.1. Первый вызов — routing only

Первый вызов к vLLM должен быть:
- дешёвым;
- коротким;
- жёстко структурированным;
- минимально контекстным.

Его задача — **semantic routing**, а не полноценное решение.

---

## 6.2. На вход router call должны идти

- текущее сообщение пользователя;
- короткий recent conversation context;
- активный mode, если он есть;
- flow state summary;
- признак последнего explicit UI action;
- список допустимых modes;
- правила mode выбора.

---

## 6.3. На выход
Строгий JSON, соответствующий `RoutingDecision`.

Пример:

```json
{
  "mode": "occasion_outfit",
  "confidence": 0.86,
  "needs_clarification": true,
  "missing_slots": ["event_type", "weather"],
  "generation_intent": false,
  "continue_existing_flow": false,
  "should_reset_to_general": false,
  "reasoning_depth": "normal"
}
```

---

## 6.4. Второй вызов — reasoning
После того как routing завершён:
- код делает retrieval;
- поднимает profile context;
- поднимает style history;
- поднимает knowledge providers;
- собирает `FashionReasoningInput`;
- только потом запускает второй вызов vLLM через `FashionReasoner`.

Это ключевое правило:  
**router не должен превращаться в полноценного reasoner.**

---

# 7. Routing input context

## 7.1. Почему нельзя слать в router всю историю
Если слать в routing весь chat log:
- растёт latency;
- растёт стоимость;
- растёт шум;
- router начинает путаться в нерелевантной старой информации;
- пропадает предсказуемость.

---

## 7.2. Что router реально должен видеть

Нужен компактный `RoutingInput`:

```python
class RoutingInput:
    user_message: str
    active_mode: str | None
    flow_state: str | None
    pending_slots: list[str]
    recent_messages: list[str]
    last_ui_action: str | None
    profile_hint_present: bool
```

---

## 7.3. Policy по памяти для routing
Routing не должен использовать полную историю.

Рекомендуемая стратегия:
- последние 2–4 user/assistant turns;
- короткое состояние текущего flow;
- summary активного контекста, если есть;
- никакой длинной исторической стенограммы.

---

# 8. Новый mode lifecycle

## 8.1. Routing должен учитывать lifecycle mode
Router должен знать:
- current active mode;
- flow state;
- не завершён ли прошлый сценарий;
- есть ли reason продолжать текущий flow;
- нужно ли сбрасывать stale state.

---

## 8.2. Новая политика mode transition

### Если:
- текущий flow закончен;
- новое сообщение не связано с ним;
- generation не requested explicitly;

тогда:
- stale mode не наследуется;
- router должен иметь право вернуть `general_advice`.

---

## 8.3. Значит
Mode selection нельзя делать как:
```text
if current_mode != idle:
    continue mode
```

Нужно делать как:
```text
if current flow still semantically active:
    continue mode
else:
    semantic re-route
```

---

# 9. ConversationRouterContext

## 9.1. Нужен отдельный контекстный объект
Чтобы router не зависел напрямую от БД и сырых ORM-объектов, нужен нормализованный объект:

```python
class ConversationRouterContext:
    active_mode: str | None
    flow_state: str | None
    pending_slots: list[str]
    recent_messages: list[ShortMessage]
    last_ui_action: str | None
    last_generation_completed: bool
    last_visual_cta_offered: bool
    profile_context_present: bool
```

---

## 9.2. Почему это важно
Это:
- изолирует router от storage representation;
- упрощает тестирование;
- уменьшает coupling;
- позволяет менять persistence без переписывания routing layer.

---

# 10. Fallback routing

## 10.1. Почему fallback всё равно нужен
Даже при semantic routing через vLLM должны быть fallback-механизмы на случай:
- timeouts;
- malformed JSON;
- router-call failure;
- degraded offline mode;
- временной недоступности vLLM.

---

## 10.2. Что должен делать fallback
Fallback не должен быть “второй полноценной логикой”.

Он должен быть минимальным:
- detect explicit style exploration button;
- detect explicit visual verbs;
- detect obvious greeting;
- detect active unfinished clarification flow.

Во всех остальных случаях fallback должен безопасно возвращать:
- `general_advice`
- без generation
- с низкой уверенностью

---

## 10.3. Архитектурно
Нужен отдельный `FallbackRouterPolicy`, а не if-цепочки внутри router service.

---

# 11. Prompt design для router call

## 11.1. Router prompt должен быть отдельным артефактом
Нельзя смешивать routing instructions и reasoning instructions.

Нужны:
- отдельный router system prompt;
- отдельная schema validation;
- отдельные router examples.

---

## 11.2. Router prompt должен:
- перечислять допустимые modes;
- описывать, когда нужен clarification;
- объяснять generation intent;
- объяснять, когда продолжать старый flow, а когда сбрасывать его;
- требовать только JSON output.

---

## 11.3. Что нельзя
Router prompt не должен:
- содержать persona prose;
- содержать длинный fashion knowledge context;
- содержать image generation instructions;
- генерировать пользовательский ответ.

---

# 12. Validation layer

## 12.1. Router output нельзя слепо доверять
Нужна обязательная валидация результата.

Нужен `RoutingDecisionValidator`, который:
- проверяет JSON schema;
- нормализует enum values;
- обрезает лишние поля;
- fallback-ит при ошибке.

---

## 12.2. Validation rules
- `mode` должен быть из разрешённого списка;
- `confidence` должен быть в диапазоне;
- `missing_slots` должен быть list[str];
- `generation_intent` должен быть bool;
- malformed output не должен ронять pipeline.

---

# 13. Оркестрация после router decision

## 13.1. Что делает orchestrator
После получения `RoutingDecision` orchestrator:
- обновляет mode/state;
- решает, нужно ли clarification;
- вызывает retrieval;
- формирует reasoning input;
- вызывает `FashionReasoner`;
- вызывает generation policy.

---

## 13.2. Что orchestrator не должен делать
Он не должен заново “угадывать” routing, если router уже отработал корректно.  
Иначе получится дублирование логики.

---

# 14. Взаимодействие routing с GenerationPolicy

## 14.1. Routing и generation policy — разные сущности
Routing отвечает:
- что это за сценарий;
- нужна ли визуализация в принципе;
- есть ли generation intent.

Generation policy отвечает:
- можно ли сейчас реально запускать generation;
- нужен ли сначала CTA;
- text-only или text+visual.

---

## 14.2. Это важно
Иначе router превратится в перегруженный God-object.

---

# 15. Interaction with profile context

## 15.1. Router должен знать о profile context только минимально
Для routing достаточно:
- есть profile context или нет;
- не хватает ли profile clarification для конкретного flow.

Router не должен строить полный fashion profile usage.

---

## 15.2. Пример
Если пользователь пишет:
> “Хочу собрать образ, но не понимаю, под какую подачу”

Router может вернуть:
- `mode = general_advice`
- `needs_clarification = true`
- `missing_slots = ["presentation_profile"]`

---

# 16. Routing и knowledge layer

## 16.1. Router не должен вытягивать полный knowledge retrieval
Это задача следующего этапа.

Но router может задавать:
- насколько глубокий reasoning потребуется;
- нужен ли historical/fashion context;
- нужен ли style retrieval;
- нужен ли stylist guidance.

---

## 16.2. Для этого достаточно hints
Например:
- `reasoning_depth = deep`
- `requires_style_retrieval = true`
- `requires_historical_layer = false`

Эти поля можно вводить либо сразу, либо во второй итерации routing redesign.

---

# 17. Clean Architecture / SOLID / OOP / FSD рекомендации

## 17.1. Domain layer
Новые сущности:
- `RoutingDecision`
- `RoutingInput`
- `ConversationRouterContext`
- `RouterFailureReason`

## 17.2. Application layer
Новые сервисы:
- `ConversationRouter`
- `FallbackRouterPolicy`
- `RoutingDecisionValidator`
- `RoutingContextBuilder`

## 17.3. Infrastructure layer
Новые адаптеры:
- `VllmRouterClient`
- router prompt template loader
- schema parser / JSON validator adapter

## 17.4. Interface layer
DTO:
- `ChatMessageRequest`
- `RoutingMetadataResponse` (внутренне или debug-only)
- admin/debug router inspection endpoints

---

## 17.5. SOLID-принципы
### SRP
- Router определяет scenario.
- Validator валидирует.
- Fallback policy деградирует.
- Orchestrator координирует.

### OCP
Новые routing rules должны добавляться через расширение policy/config, а не через переписывание базового router service.

### DIP
Application layer должен зависеть от интерфейса router client, а не от конкретного vLLM implementation.

---

# 18. Frontend implications

## 18.1. Frontend не делает routing
Frontend не должен сам определять scenario по тексту.  
Он только:
- отправляет сообщение;
- может передавать explicit UI action;
- отображает ответ.

---

## 18.2. Что frontend может передать
- `ui_action = try_other_style`
- `ui_action = confirm_visualization`
- `ui_action = none`

Эти hints помогают router, но не заменяют его.

---

# 19. Наблюдаемость и дебаг routing

## 19.1. Что нужно логировать
Для каждого routing decision:
- session id
- user message hash / excerpt
- active mode before
- routing decision
- confidence
- fallback used or not
- validation errors
- elapsed time

---

## 19.2. Зачем
Routing — это критический decision layer. Без наблюдаемости он быстро станет чёрным ящиком.

---

# 20. Тестирование

## 20.1. Unit tests
Нужно покрыть:
- `RoutingDecisionValidator`
- `FallbackRouterPolicy`
- `RoutingContextBuilder`

## 20.2. Integration tests
- router call returns valid decision
- malformed router output degrades safely
- stale mode resets correctly
- explicit style button always routes to `style_exploration`

## 20.3. Product-level tests
Проверить кейсы:
- `привет` → `general_advice`
- “что надеть на выставку вечером?” → `occasion_outfit` or conversational styling mode
- “собери flat lay” → generation_intent = true
- после style exploration → свободный ввод → `general_advice`

---

# 21. Поэтапный план реализации

## Подэтап 1. Зафиксировать routing contract
- описать `RoutingInput`
- описать `RoutingDecision`
- описать допустимые modes

## Подэтап 2. Сделать `RoutingContextBuilder`
- собирать короткий context
- убрать зависимость от сырых ORM-объектов

## Подэтап 3. Реализовать `VllmRouterClient`
- отдельный prompt
- отдельный JSON schema
- отдельный timeout / retry policy

## Подэтап 4. Реализовать `RoutingDecisionValidator`
- strict schema validation
- graceful fallback

## Подэтап 5. Реализовать `FallbackRouterPolicy`
- minimal deterministic routing
- safe default to `general_advice`

## Подэтап 6. Подключить `ConversationRouter` в orchestrator
- заменить main keyword routing
- оставить keyword routing только fallback-механизмом

## Подэтап 7. Обновить state lifecycle
- stale mode reset
- continue_existing_flow logic
- post-generation reset compatibility

## Подэтап 8. Добавить observability и tests
- router logs
- integration tests
- product scenario tests

---

# 22. Acceptance criteria

Этап считается завершённым, если:

1. Основной mode detection делает `ConversationRouter`, а не keyword if-chain.
2. Router использует отдельный короткий vLLM call с JSON output.
3. Routing и reasoning разделены на два разных этапа.
4. Keyword routing остаётся только fallback.
5. Router умеет:
   - определять scenario;
   - видеть generation intent;
   - требовать clarification;
   - решать continue/reset active flow.
6. Malformed router output не ломает pipeline.
7. После visual flow stale mode не наследуется автоматически.
8. Frontend не содержит сценарной бизнес-логики routing.
9. Есть unit + integration + product tests.
10. Routing decisions логируются и пригодны для отладки.

---

# 23. Definition of Done

Этап реализован корректно, если:
- routing стал semantic-first;
- mode lifecycle перестал зависеть от ключевых слов;
- state machine управляется явно и предсказуемо;
- следующий этап (`FashionReasoner`) можно строить поверх уже устойчивого routing layer;
- система стала расширяемой под новые сценарии и новые knowledge providers.

---

# 24. Архитектурный итог этапа

После реализации routing redesign система перестаёт “угадывать сценарий по словам” и начинает **понимать тип запроса семантически**. Это создаёт фундамент для:
- text-first UX;
- устойчивого generation policy;
- корректной работы profile context;
- будущего подключения Малевича, историка моды и стилиста;
- чистого разделения между mode detection, retrieval, reasoning и generation.

Именно этот этап превращает текущий диалоговый runtime из набора правил в **настоящий orchestration pipeline**, где vLLM используется там, где он действительно силён: в semantic interpretation пользовательского намерения.
