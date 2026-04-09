
# Этап 2. Нормализовать frontend как тонкий UI, а не место логики

## Контекст этапа

В архитектурном плане проекта Stage 2 сформулирован как переход от "умного фронтенда" к **тонкому UI**, который передаёт намерение пользователя и отображает состояние сценария, но не принимает бизнес-решения сам. План прямо фиксирует, что quick actions должны передавать только режим и сообщение, frontend не должен сам решать, запускать генерацию или нет, а также должен использовать отдельный payload для chat command и не зависеть логикой от наличия asset. citeturn750170view0

Этот этап опирается на Stage 1, где уже должны быть зафиксированы:
- доменная модель режимов;
- state machine по сценариям;
- единый `ChatModeContext`;
- типизированный `DecisionResult`.

Frontend на этом этапе **не должен дублировать решения backend orchestration layer**. Его задача — быть надёжным интерфейсом между:
- действием пользователя,
- backend API,
- отображением сценарного состояния,
- асинхронной генерацией.

---

# 1. Цель этапа

Превратить frontend из места, где:
- размазана бизнес-логика;
- случайно выбирается тип запроса;
- логика зависит от asset, таймаутов и UI-эвристик;
- follow-up сообщения теряют смысл сценария;

в систему, где frontend:
- передаёт backend **семантически правильный command payload**;
- отражает состояние сценария, пришедшее с backend;
- не решает, нужна ли генерация;
- не реконструирует смысл предыдущих шагов;
- не хранит сценарную истину только локально;
- работает одинаково для sync и async режимов.

---

# 2. Архитектурные принципы

## 2.1. Clean Architecture

### Domain
Frontend не должен содержать бизнес-правил домена. Он может содержать только:
- domain types, импортированные как контракт;
- отображение этих типов в UI.

### Application
Frontend может содержать application-level orchestration только для:
- вызова API;
- подписки на статус job;
- нормализации server response для экрана.

### Infrastructure
Все детали транспорта:
- HTTP client
- polling / SSE / websocket
- error mapping
- retry policy
должны жить в infrastructure/data слое фронтенда, а не в UI-компонентах.

### Interface
Компоненты, виджеты, хуки и страницы должны быть thin interface layer.

---

## 2.2. SOLID

### Single Responsibility Principle
Каждый модуль фронтенда должен иметь одну роль:
- компонент — отображает;
- command dispatcher — отправляет команду;
- status subscriber — следит за job;
- adapter — приводит DTO к UI model.

### Open/Closed Principle
Новый режим чата должен добавляться:
- через новый command config;
- новый UI mapping;
- новый backend mode contract,
без переписывания существующих quick actions.

### Liskov Substitution Principle
Все command handlers должны реализовывать единый контракт вызова:
- `sendCommand(payload)`
- `sendMessage(payload)`
- `subscribeToJob(jobId)`

### Interface Segregation Principle
Frontend не должен иметь один "толстый" API client. Нужны отдельные интерфейсы:
- chat command API;
- chat message API;
- generation status API;
- session context API.

### Dependency Inversion Principle
UI зависит не от `fetch/axios` напрямую, а от абстракций:
- `ChatGateway`
- `CommandGateway`
- `GenerationGateway`

---

## 2.3. FSD (Feature-Sliced Design)

Frontend должен быть разрезан по предметной области и пользовательским возможностям.

Рекомендуемая структура:

```text
src/
  app/
    providers/
    router/
  processes/
    stylist-chat/
      model/
      lib/
  pages/
    stylist-chat/
  widgets/
    stylist-chat-panel/
    quick-actions/
    chat-thread/
    generation-status/
  features/
    send-chat-message/
    run-chat-command/
    attach-garment-asset/
    retry-generation/
    followup-clarification/
  entities/
    chat-session/
    chat-message/
    command/
    generation-job/
    stylist-context/
  shared/
    api/
    config/
    lib/
    model/
    ui/
```

### Принцип
- `entities` — базовые сущности UI уровня;
- `features` — атомарные действия пользователя;
- `widgets` — собранные блоки интерфейса;
- `processes` — многошаговые UI-сценарии;
- `shared` — переиспользуемые примитивы.

---

# 3. Главная архитектурная проблема текущего frontend

Согласно плану, текущий frontend частично сам решает:
- какой сценарий сейчас активен;
- когда нужно передавать intent;
- когда запускать генерацию;
- нужен ли asset как обязательное условие;
- как интерпретировать follow-up. citeturn750170view0

Такой подход приводит к системным проблемам:
1. frontend и backend могут расходиться в понимании активного режима;
2. follow-up сообщения теряют контекст;
3. режимы команд зависят от случайных UI условий;
4. тестировать сценарии становится трудно;
5. любое усложнение backend оркестратора вынуждает переписывать frontend.

Этап 2 должен устранить это полностью.

---

# 4. Роль frontend после нормализации

Frontend становится **тонким клиентом сценарного backend**.

Он должен уметь только четыре вещи:

1. **инициировать команду**;
2. **отправить обычное сообщение**;
3. **отобразить текущее состояние сценария**;
4. **следить за статусом generation job**.

Он **не должен**:
- сам определять, завершён ли сценарий;
- решать, когда backend должен генерировать;
- склеивать command flow по таймаутам;
- решать, что отсутствие asset = запрет на `garment_matching`;
- держать критичный state только в локальном React-state.

---

# 5. Доменный контракт frontend ↔ backend

## 5.1. Единый command payload

Stage 2 прямо требует отдельный payload для chat command. В плане приводится пример полей:
- `session_id`
- `requested_intent`
- `command_name`
- `message`
- `asset_id`
- `command_step` citeturn750170view0

Рекомендуемый расширенный контракт:

```ts
type ChatCommandPayload = {
  sessionId: string;
  requestedIntent: "general_advice" | "garment_matching" | "style_exploration" | "occasion_outfit";
  commandName: "garment_matching" | "style_exploration" | "occasion_outfit";
  commandStep: "start" | "followup" | "resume";
  message: string | null;
  assetId: string | null;
  metadata?: {
    source: "quick_action" | "chat_input" | "retry" | "system_resume";
    clientMessageId?: string;
    uiLocale?: string;
  };
};
```

### Архитектурный смысл
- `requestedIntent` — режим;
- `commandName` — пользовательская команда как UX-событие;
- `commandStep` — стадия client-side interaction, но не бизнес-логика;
- `message` — пользовательский текст, если он есть;
- `assetId` — опциональный input;
- `metadata` — только технический контекст.

---

## 5.2. Separate payload для обычного сообщения

Обычное сообщение должно иметь отдельный контракт:

```ts
type ChatMessagePayload = {
  sessionId: string;
  message: string;
  requestedIntent?: "general_advice" | "garment_matching" | "style_exploration" | "occasion_outfit" | null;
  metadata?: {
    source: "chat_input" | "followup" | "system_retry";
    clientMessageId?: string;
  };
};
```

### Почему нельзя всё слить в один payload
Потому что:
- команда — это намерение войти в сценарий;
- обычное сообщение — это сообщение внутри сценария или вне него;
- разные payload легче логировать, тестировать и расширять.

---

## 5.3. Unified response contract

Frontend должен получать типизированный результат, а не угадывать по комбинации полей.

```ts
type ChatResponse =
  | {
      decisionType: "text_only";
      activeMode: string;
      flowState: string;
      replyText: string;
      jobId: null;
      context: FrontendScenarioContext;
    }
  | {
      decisionType: "clarification_required";
      activeMode: string;
      flowState: string;
      replyText: string;
      clarificationKind: string;
      jobId: null;
      context: FrontendScenarioContext;
    }
  | {
      decisionType: "text_and_generate";
      activeMode: string;
      flowState: string;
      replyText: string;
      jobId: string;
      context: FrontendScenarioContext;
    }
  | {
      decisionType: "generation_only";
      activeMode: string;
      flowState: string;
      replyText: null;
      jobId: string;
      context: FrontendScenarioContext;
    }
  | {
      decisionType: "error_recoverable";
      activeMode: string;
      flowState: string;
      replyText: string;
      jobId: null;
      context: FrontendScenarioContext;
    };
```

### Выгода
Frontend перестаёт делать `if (image && intent && autoGenerate && ...)`.
Он просто рендерит ответ по `decisionType`.

---

# 6. Frontend state: что хранить, а что не хранить

## 6.1. Что frontend имеет право хранить локально

Локальный state допустим для:
- текущего значения input;
- UI mode открытых панелей;
- optimistic messages;
- progress indicators;
- локального статуса отправки;
- временного выбора файла / asset preview.

## 6.2. Что frontend НЕ должен считать источником истины

Не должен локально как истину хранить:
- активный business mode;
- pending clarification;
- slot completeness;
- решение о запуске генерации;
- `should_auto_generate`;
- завершённость сценария.

Это должно приходить с backend как часть `context`.

---

## 6.3. FrontendScenarioContext

Frontend должен иметь "зеркальный" read-only контекст, полученный с backend:

```ts
type FrontendScenarioContext = {
  activeMode: "general_advice" | "garment_matching" | "style_exploration" | "occasion_outfit";
  flowState: string;
  pendingClarification: boolean;
  clarificationKind: string | null;
  currentJobId: string | null;
  commandName: string | null;
  canSendFreeformMessage: boolean;
  canAttachAsset: boolean;
};
```

### Назначение
Не чтобы frontend принимал решения вместо backend, а чтобы:
- показывать правильный placeholder;
- отключать/включать нужные UI элементы;
- правильно оформлять follow-up сообщение.

---

# 7. Quick actions как thin command emitters

## 7.1. Что такое quick action после нормализации

Quick action — это **не сценарный движок**.  
Это просто UI-trigger, который отправляет команду backend.

Например:

### Garment Matching
Кнопка отправляет:
```json
{
  "requestedIntent": "garment_matching",
  "commandName": "garment_matching",
  "commandStep": "start",
  "message": null
}
```

### Style Exploration
```json
{
  "requestedIntent": "style_exploration",
  "commandName": "style_exploration",
  "commandStep": "start",
  "message": null
}
```

### Occasion Outfit
```json
{
  "requestedIntent": "occasion_outfit",
  "commandName": "occasion_outfit",
  "commandStep": "start",
  "message": null
}
```

### Смысл
Кнопка больше не запускает локальную бизнес-цепочку. Она только сообщает backend:
> пользователь хочет войти в сценарий X

---

## 7.2. Что quick actions не должны делать

Они не должны:
- формировать финальный текст запроса;
- решать, нужен ли follow-up;
- решать, запускать ли generation;
- проверять asset перед отправкой;
- хранить сценарную логику в callback.

---

# 8. Follow-up сообщения

## 8.1. Проблема
Сейчас follow-up сообщения в action modes легко могут интерпретироваться как новый обычный чат.

## 8.2. Решение
Frontend должен отправлять follow-up как обычное сообщение, но с метаданными:
- `source = "followup"`
- текущий `sessionId`
- без локального угадывания режима;
- backend сам продолжает активный сценарий по `ChatModeContext`.

### Принцип
Frontend **не восстанавливает** сценарий из памяти.  
Он передаёт сообщение и отображает то, что сказал backend.

---

# 9. Работа с asset

Stage 2 требует убрать фронтовую зависимость логики от наличия asset для `garment_matching`. Это отдельное прямое требование плана. citeturn750170view0

## 9.1. Правильная роль asset
Asset — это опциональный enrich input.

Он может:
- повысить точность;
- дополнить текст;
- улучшить подбор;
но не определяет, доступен ли сам режим.

## 9.2. Архитектурное правило
Frontend должен:
- уметь прикладывать `assetId`;
- не запрещать запуск `garment_matching`, если asset нет;
- не держать в UI условиях ветку "если нет asset — отправить как general chat".

---

# 10. Асинхронная генерация как first-class UI flow

План проекта требует generation jobs и очереди как обязательный слой, а не длинный HTTP-сценарий. citeturn750170view0

Stage 2 должен подготовить frontend под это.

## 10.1. Что должен уметь frontend
- получать `jobId`;
- подписываться на статус job;
- отображать состояния:
  - `queued`
  - `in_progress`
  - `completed`
  - `failed`
- догружать результат отдельно от chat response.

## 10.2. Чего делать нельзя
Нельзя:
- ждать изображение в том же UI действии как обычный sync response;
- блокировать весь чат до конца генерации;
- связывать "ответ сервера" и "готовое изображение" как одну атомарную синхронную сущность.

## 10.3. Recommended UI contract
После `text_and_generate` frontend:
1. рендерит текст;
2. показывает generation placeholder;
3. подписывается на job status;
4. подставляет результат по готовности.

---

# 11. FSD-декомпозиция по модулям

## 11.1. Entities

### `entities/chat-message`
- message model
- message DTO adapters
- render helpers

### `entities/chat-session`
- session model
- scenario context model

### `entities/command`
- `ChatCommandPayload`
- command type guards
- intent enums

### `entities/generation-job`
- generation job model
- status enum
- job response DTO

---

## 11.2. Features

### `features/run-chat-command`
Отправка quick actions.

Содержит:
- `runCommand(payload)`
- command validation
- UI trigger adapters

### `features/send-chat-message`
Обычные и follow-up сообщения.

### `features/attach-garment-asset`
Загрузка asset и получение `assetId`.

### `features/retry-generation`
Повтор асинхронной генерации.

---

## 11.3. Widgets

### `widgets/quick-actions`
Только кнопки и привязка к command payload.

### `widgets/chat-thread`
Только отображение истории сообщений и generation placeholders.

### `widgets/generation-status`
Отображение статуса job.

### `widgets/stylist-chat-panel`
Композиция всех частей.

---

## 11.4. Processes

### `processes/stylist-chat`
UI-уровневая координация:
- загрузка сессии;
- отправка команд;
- отправка follow-up;
- подписка на generation jobs;
- обновление thread.

Важно: это **не место бизнес-логики домена**, а место coordination logic интерфейса.

---

# 12. OOP-модель frontend

## 12.1. Где OOP уместен
Для frontend с React и FSD не нужен "классический ООП everywhere", но OOP полезен в виде:
- value objects;
- gateway interfaces;
- adapters;
- service classes для транспорта.

### Примеры

#### `ChatGateway`
```ts
interface ChatGateway {
  sendMessage(payload: ChatMessagePayload): Promise<ChatResponse>;
}
```

#### `CommandGateway`
```ts
interface CommandGateway {
  runCommand(payload: ChatCommandPayload): Promise<ChatResponse>;
}
```

#### `GenerationGateway`
```ts
interface GenerationGateway {
  getStatus(jobId: string): Promise<GenerationJobState>;
}
```

#### `ChatResponseAdapter`
Класс/модуль, который переводит server DTO в UI model.

## 12.2. Где OOP не нужен
- в презентационных компонентах;
- в примитивных UI-хуках;
- в простых render helpers.

---

# 13. Антипаттерны, которые надо убрать

## 13.1. Frontend deciding business outcomes
Плохо:
- `if (asset) intent = garment_matching else general_advice`
- `if (message contains ...) autoGenerate = true`
- `if (style button clicked twice) generate immediately with local seed`

## 13.2. Smart hooks with hidden business logic
Плохо, когда один хук:
- собирает payload;
- интерпретирует режим;
- управляет таймаутом;
- решает, нужен ли polling;
- сам знает все backend ветки.

## 13.3. UI-driven scenario truth
Плохо, когда UI считает:
- "мы сейчас в occasion mode"
только потому что нажата кнопка,
а backend уже думает иначе.

## 13.4. Asset-driven gating
Плохо, когда наличие/отсутствие изображения меняет сам доменный режим.

---

# 14. План реализации Stage 2

## Подэтап 2.1. Зафиксировать frontend contracts
Создать:
- `ChatCommandPayload`
- `ChatMessagePayload`
- `ChatResponse`
- `FrontendScenarioContext`
- `GenerationJobState`

## Подэтап 2.2. Вынести API слой в отдельные gateways
Создать:
- `chatGateway`
- `commandGateway`
- `generationGateway`

UI не должен использовать `fetch` напрямую.

## Подэтап 2.3. Переписать quick actions как command emitters
Каждая кнопка:
- формирует только command payload;
- не решает ничего кроме "какую команду отправить".

## Подэтап 2.4. Развести обычные сообщения и командные payload
Отдельные handlers:
- `sendFreeformMessage`
- `sendFollowupMessage`
- `runQuickActionCommand`

## Подэтап 2.5. Сделать scenario-aware UI rendering
Placeholder, подсказки, статус генерации — только по server context.

## Подэтап 2.6. Подготовить async generation UX
Добавить:
- generation placeholders,
- job polling/SSE,
- message-to-job mapping.

## Подэтап 2.7. Написать contract tests
Проверять:
- quick action формирует правильный payload;
- follow-up не меняет режим локально;
- отсутствие asset не запрещает garment mode;
- `text_and_generate` рендерится как текст + pending image.

---

# 15. Критерии готовности этапа

Этап 2 выполнен правильно, если:

1. Frontend больше не содержит доменных решений о генерации.
2. Все quick actions отправляют типизированный command payload.
3. Follow-up сообщения не используют локальные эвристики выбора режима.
4. Наличие asset не является gatekeeper для `garment_matching`.
5. UI отображает состояние сценария на основе server context.
6. Генерация поддерживает async lifecycle через `jobId`.
7. Компоненты не знают про детали HTTP и backend веток.
8. Новую команду можно добавить без переписывания существующих quick actions.

---

# 16. Архитектурный итог этапа

После Stage 2 frontend должен стать:

- тонким UI-слоем;
- устойчивым к изменениям backend orchestration;
- удобным для тестирования;
- совместимым с async generation;
- пригодным для роста числа режимов и knowledge-driven поведения.

Именно после такого фронтенда backend orchestration и state machines смогут работать стабильно, без борьбы с логикой, размазанной между клиентом и сервером.
