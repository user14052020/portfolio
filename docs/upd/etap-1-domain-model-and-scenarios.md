
# Этап 1. Зафиксировать доменную модель и сценарии

## Цель этапа

Этап 1 нужен для того, чтобы перестать воспринимать fashion stylist chat как один общий чат с "магическим" LLM внутри и превратить его в управляемую систему со строгой доменной моделью, предсказуемыми сценариями и устойчивым session state.

На этом этапе мы **не чиним частные баги точечно** и **не переписываем генерацию целиком**. Мы создаём фундамент, на котором потом уже можно без хаоса реализовать:

- корректные текстовые ответы;
- стабильную работу трёх быстрых команд;
- отсутствие silent failure после уточнений;
- анти-повтор в `style_exploration`;
- масштабируемый orchestrator;
- удобное тестирование и наблюдаемость.

Этот этап логически вытекает из общего архитектурного плана проекта, где система должна быть разделена на 4 режима: `general_advice`, `garment_matching`, `style_exploration`, `occasion_outfit`, а follow-up сообщения не должны терять свой сценарный контекст.

---

## Результат этапа

После завершения Этапа 1 в проекте должны появиться:

1. **Единая доменная модель чата**, описывающая, что такое режим, шаг сценария, уточнение, генерация, контекст мероприятия, anchor garment, история стилей и т.д.
2. **Единый объект session state** для backend, который сериализуется, читается и обновляется по строгим правилам.
3. **Явно описанные state machine** для 4 режимов.
4. **Контракты сценариев**: что считается входом, чего не хватает, когда задавать уточнение, когда обязательно создавать generation job.
5. **Явные переходы между состояниями** вместо "угадывания по тексту".
6. **Соглашения по backend API payload** для последующего фронтенда и оркестратора.
7. **Набор сценарных тест-кейсов**, по которым дальше будут реализовываться Этапы 2+.

---

## Что именно решает Этап 1

Сейчас у проекта есть несколько системных причин нестабильности:

- intent теряется или угадывается заново;
- follow-up сообщения интерпретируются как новый общий запрос;
- сценарии быстрых команд не живут как полноценные stateful flow;
- generation может не запускаться, хотя для режима это обязательное завершение;
- часть логики зависит от текста пользователя, а не от состояния сценария;
- не зафиксировано, какие поля состояния обязательны и когда.

Этап 1 решает это за счёт того, что вводит:
- язык предметной области;
- границы ответственности;
- типы состояния;
- конечные автоматы;
- правила переходов.

---

# 1. Доменная модель

## 1.1. Главные сущности

Ниже — сущности, которые должны существовать в системе как часть backend domain layer.

### ChatMode
Перечень режимов:

- `general_advice`
- `garment_matching`
- `style_exploration`
- `occasion_outfit`

Режим — это не "подсказка фронта", а главный способ интерпретации текущего сценария.

---

### ChatModeContext
Главный объект, который хранится в session state и описывает, **что сейчас происходит в разговоре**.

Минимальный состав полей:

- `active_mode`
- `requested_intent`
- `flow_state`
- `pending_clarification`
- `clarification_kind`
- `clarification_attempts`
- `should_auto_generate`
- `anchor_garment`
- `occasion_context`
- `style_history`
- `last_generation_prompt`
- `last_generated_outfit_summary`
- `conversation_memory`
- `command_context`
- `current_style_id`
- `current_style_name`
- `current_job_id`
- `last_decision_type`
- `updated_at`

### Назначение
`ChatModeContext` должен быть **единственным источником истины** о том, в каком режиме находится пользователь и чего система ждёт дальше.

---

### FlowState
Отдельный enum состояния сценария.

Рекомендуемый минимум:

- `idle`
- `awaiting_user_message`
- `awaiting_anchor_garment`
- `awaiting_occasion_details`
- `awaiting_clarification`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`
- `recoverable_error`

### Назначение
`FlowState` нужен, чтобы backend не угадывал по последнему сообщению "это новое сообщение или продолжение сценария". Система должна знать это явно.

---

### ClarificationKind
Тип уточнения, который сейчас ожидается.

Примеры:

- `anchor_garment_description`
- `anchor_garment_missing_attributes`
- `occasion_event_type`
- `occasion_dress_code`
- `occasion_desired_impression`
- `occasion_missing_multiple_slots`
- `style_preference`
- `general_followup`

### Назначение
Позволяет:
- задавать точные follow-up вопросы;
- не путать общий чат с заполнением слотов;
- логировать, где сценарий тормозит.

---

### AnchorGarment
Структурированное представление вещи, вокруг которой строится образ.

Поля:

- `raw_user_text`
- `garment_type`
- `color`
- `secondary_colors`
- `material`
- `fit`
- `silhouette`
- `seasonality`
- `formality`
- `gender_context`
- `confidence`
- `is_sufficient_for_generation`

### Назначение
Команда `garment_matching` не должна работать на неструктурированном тексте до самого конца. После ответа пользователя нужна нормализация в `AnchorGarment`.

---

### OccasionContext
Структурированный контекст мероприятия.

Минимальные поля:

- `event_type`
- `location`
- `time_of_day`
- `season`
- `dress_code`
- `weather_context`
- `desired_impression`
- `constraints`
- `is_sufficient_for_generation`

### Назначение
Команда `occasion_outfit` должна быть реализована как slot-filling flow, а не как свободная переписка.

---

### StyleDirection
Нормализованное описание одного стилевого направления, использованного ранее в `style_exploration`.

Поля:

- `style_id`
- `style_name`
- `palette`
- `silhouette`
- `hero_garments`
- `footwear`
- `accessories`
- `materials`
- `styling_mood`
- `composition_type`
- `background_family`
- `created_at`

### Назначение
Нужно для anti-repeat и semantic diversity.

---

### GenerationIntent
Отдельная сущность, которая описывает **почему** сейчас запускается генерация.

Поля:

- `mode`
- `trigger`
- `reason`
- `must_generate`
- `job_priority`
- `source_message_id`

### Назначение
Позволяет отделить "система решила дать текст" от "режим требует обязательной генерации".

---

### DecisionResult
Типизированный результат работы orchestrator/decision layer.

Возможные варианты:

- `text_only`
- `clarification_required`
- `text_and_generate`
- `generation_only`
- `error_recoverable`
- `error_hard`

### Назначение
Убирает неявное поведение и silent failure.

---

## 1.2. Инварианты доменной модели

На уровне backend должны быть зафиксированы правила, которые никогда не нарушаются.

### Общие инварианты
1. В любой момент у сессии есть один `active_mode`.
2. Если `flow_state != idle`, follow-up интерпретируется как продолжение сценария.
3. Если система ждёт уточнение, новое сообщение пользователя сначала идёт в state machine, а не в общий LLM роутинг.
4. Генерация не должна запускаться "случайно"; она должна быть следствием `DecisionResult`.
5. Для `garment_matching`, `style_exploration`, `occasion_outfit` генерация — это часть доменного сценария, а не опциональный side effect.
6. `ChatModeContext` обновляется атомарно на каждый шаг.

### Специфические инварианты по режимам
- `garment_matching`: если есть достаточный `anchor_garment`, режим обязан перейти к generation.
- `style_exploration`: если есть запрос на новый стиль, в decision должны учитываться предыдущие `style_history`.
- `occasion_outfit`: если минимальный набор slot’ов заполнен, сценарий не должен оставаться в уточнении.
- `general_advice`: по умолчанию текстовый, без обязательной генерации.

---

# 2. State machine по режимам

## 2.1. General Advice

### Назначение
Свободный текстовый стилистический чат.

### Состояния
- `idle`
- `awaiting_user_message`
- `ready_for_decision`
- `completed`

### Переходы
1. Пользователь пишет свободное сообщение.
2. Система интерпретирует сообщение как `general_advice`.
3. Decision layer формирует текстовый ответ.
4. Сценарий завершается.
5. Опционально система предлагает перейти в один из action-режимов.

### Ограничения
- follow-up не должен случайно включать generation, если нет явного перехода в action-mode;
- conversation memory может использоваться, но без жёстких slot-моделей.

---

## 2.2. Garment Matching

### Назначение
Подбор образа вокруг одной вещи.

### Ключевая особенность
После нажатия кнопки команда должна перейти в **режим ожидания описания вещи**, а не сразу в LLM-чат.

### Состояния
- `idle`
- `awaiting_anchor_garment`
- `awaiting_clarification`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`

### Базовый сценарий
1. Пользователь нажимает "Подобрать к вещи".
2. Session state:
   - `active_mode = garment_matching`
   - `flow_state = awaiting_anchor_garment`
   - `should_auto_generate = true`
3. Таймаут 60 секунд не завершает сценарий.
4. Бот отправляет служебное уточнение: "Опиши вещь, к которой нужно подобрать образ".
5. Пользователь отвечает.
6. Ответ пользователя парсится в `AnchorGarment`.
7. Если данных недостаточно:
   - `flow_state = awaiting_clarification`
   - задаётся одно короткое уточнение.
8. Если данных достаточно:
   - `flow_state = ready_for_decision`
   - строится outfit brief
   - `flow_state = ready_for_generation`
   - создаётся generation job
9. Пользователь получает текст + изображение.

### Жёсткие правила
- режим не должен возвращаться в `general_advice`, пока не завершён;
- наличие asset — опционально;
- текстовый совет без генерации не является штатным финалом режима.

---

## 2.3. Style Exploration

### Назначение
Сгенерировать новый стиль, который отличается от предыдущего не только сидом, но и смыслово.

### Состояния
- `idle`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`

### Базовый сценарий
1. Пользователь нажимает "Попробовать другой стиль".
2. Session state:
   - `active_mode = style_exploration`
   - `flow_state = ready_for_decision`
   - `should_auto_generate = true`
3. Система достаёт:
   - текущий стиль или seed style;
   - `style_history` последних 3–5 style directions;
   - knowledge profile выбранного стиля;
   - diversity constraints.
4. Decision layer строит **новый style brief**.
5. Если brief валиден:
   - `flow_state = ready_for_generation`
   - создаётся generation job.
6. После завершения генерации:
   - обновляется `style_history`;
   - сценарий переходит в `completed`.

### Жёсткие правила
- semantic diversity обязательна;
- visual diversity обязательна;
- повтор ключевых элементов предыдущей генерации должен быть исключён или явно ограничен.

---

## 2.4. Occasion Outfit

### Назначение
Подбор наряда под событие.

### Ключевая особенность
Это сценарий slot-filling, а не свободный разговор.

### Минимальные слоты
- `event_type`
- `time_of_day`
- `season`
- `dress_code` или `desired_impression`

### Состояния
- `idle`
- `awaiting_occasion_details`
- `awaiting_clarification`
- `ready_for_decision`
- `ready_for_generation`
- `generation_queued`
- `generation_in_progress`
- `completed`

### Базовый сценарий
1. Пользователь нажимает "Что надеть на событие".
2. Session state:
   - `active_mode = occasion_outfit`
   - `flow_state = awaiting_occasion_details`
   - `should_auto_generate = true`
3. Бот задаёт первый вопрос.
4. Ответ пользователя записывается в `OccasionContext`.
5. Если минимального набора данных недостаточно:
   - задаётся строгое уточнение по недостающему слоту.
6. Если данных достаточно:
   - `flow_state = ready_for_decision`
   - строится outfit brief
   - `flow_state = ready_for_generation`
   - создаётся generation job
7. Возвращается текст + изображение.

### Жёсткие правила
- follow-up не должен интерпретироваться как новое текстовое сообщение;
- если контекста уже достаточно, система не должна молчать или снова спрашивать "в общем".

---

# 3. Session state: требования к реализации

## 3.1. Где должен жить state

`ChatModeContext` должен жить в backend session storage, а не только:
- во фронтенд state;
- в последнем сообщении;
- в LLM промпте;
- в эвристиках по тексту.

Реализация может быть:
- JSONB в БД сессий;
- отдельная таблица chat_session_context;
- сериализованная структура в Redis с durable snapshot в БД.

Для масштабируемости лучший вариант:
- **источник истины в БД**
- **опциональный кэш в Redis**

---

## 3.2. Требования к обновлению state

Каждое пользовательское сообщение должно проходить так:

1. Загрузка текущего `ChatModeContext`.
2. Проверка активного сценария.
3. Применение state transition.
4. Сохранение нового состояния.
5. Передача управления decision/orchestration layer.

### Важно
Сохранение состояния должно происходить до вызова генерации, иначе возможны:
- дубли;
- silent failure;
- потеря `job_id`;
- расхождение UI и backend.

---

## 3.3. Версионирование state

У `ChatModeContext` должен быть:
- `version`
- `updated_at`
- `updated_by_message_id`

Это поможет:
- безопасно эволюционировать схему;
- мигрировать старые сессии;
- отлаживать проблемные сценарии.

---

# 4. Контракты входа и выхода

## 4.1. Входной payload от frontend

На этом этапе нужно зафиксировать, какой payload backend должен принимать независимо от реализации фронта.

Минимальный payload:

```json
{
  "session_id": "string",
  "message": "string",
  "requested_intent": "general_advice | garment_matching | style_exploration | occasion_outfit | null",
  "command_name": "string | null",
  "command_step": "string | null",
  "asset_id": "string | null",
  "metadata": {}
}
```

### Принцип
Frontend не должен быть местом бизнес-логики. Его задача — передать:
- пользовательское сообщение,
- режим,
- идентификаторы,
- опциональный контекст команды.

---

## 4.2. Выход orchestrator layer

Внутренний контракт результата должен быть типизирован.

Пример:

```json
{
  "decision_type": "clarification_required | text_only | text_and_generate | generation_only | error_recoverable",
  "active_mode": "garment_matching",
  "flow_state": "awaiting_clarification",
  "text_reply": "Опиши цвет и материал вещи",
  "generation_payload": null,
  "job_id": null,
  "context_patch": {}
}
```

### Польза
Так убирается "тишина":
- либо есть уточнение,
- либо есть текст,
- либо есть job,
- либо есть recoverable error.

---

# 5. Реализация на уровне модулей

## 5.1. Что должно появиться в кодовой базе

На Этапе 1 рекомендуется создать или зафиксировать следующие модули:

### `domain/chat_modes.py`
Содержит:
- enum режимов;
- enum flow states;
- enum clarification kinds.

### `domain/chat_context.py`
Содержит:
- `ChatModeContext`
- `AnchorGarment`
- `OccasionContext`
- `StyleDirection`
- `GenerationIntent`

### `domain/decision_result.py`
Содержит:
- типы результата orchestrator;
- сериализацию результата.

### `domain/state_machine/`
Папка с отдельными state machine по режимам:
- `general_advice_machine.py`
- `garment_matching_machine.py`
- `style_exploration_machine.py`
- `occasion_outfit_machine.py`

### `services/chat_context_store.py`
Абстракция хранения и обновления `ChatModeContext`.

### `services/chat_mode_resolver.py`
Компонент, который определяет:
- использовать ли `requested_intent`;
- продолжать ли текущий режим;
- разрешён ли переход между режимами.

---

## 5.2. Что не надо делать на этом этапе

Чтобы не сломать архитектуру, на Этапе 1 **не надо**:

- переписывать Comfy workflow;
- менять модель LLM;
- улучшать prompt builder точечно;
- вносить хаотичные условия во frontend;
- лечить баги через if/else в роуте;
- строить knowledge retrieval без доменного контракта.

---

# 6. Тестовые сценарии этапа

Этап 1 считается завершённым только если есть сценарные тесты.

## 6.1. General Advice
- обычный текстовый вопрос;
- follow-up без смены режима;
- явный переход в command mode.

## 6.2. Garment Matching
- вход через quick action;
- ожидание описания вещи;
- неполное описание → одно уточнение;
- полное описание → генерация.

## 6.3. Style Exploration
- первый запуск;
- второй запуск с заполненной историей;
- проверка, что сценарий не падает в общий чат.

## 6.4. Occasion Outfit
- вход через quick action;
- уточнение по слоту;
- follow-up попадает в `OccasionContext`;
- при достаточном контексте создаётся generation job.

---

# 7. Критерии готовности этапа

Этап 1 реализован правильно, если:

1. У каждого режима есть явный state machine.
2. Session state не восстанавливается "по памяти" из текста.
3. Follow-up не ломает сценарий.
4. `garment_matching` и `occasion_outfit` не зависят от таймаута 60 секунд как от управляющей логики.
5. `style_exploration` имеет явную модель history/diversity.
6. Есть типизированный `DecisionResult`.
7. Есть минимум по одному e2e-сценарию на каждый режим.
8. В коде стало возможно локализовать баг: mode / state / decision / generation.

---

# 8. Практический порядок внедрения

## Подэтап 1
Зафиксировать Python/TypeScript типы:
- enums;
- dataclasses / pydantic models;
- DecisionResult.

## Подэтап 2
Сделать `ChatModeContext` storage abstraction.

## Подэтап 3
Реализовать state machine для `garment_matching` и `occasion_outfit`, потому что они больше всего страдают от потери follow-up контекста.

## Подэтап 4
Реализовать state machine для `style_exploration` с `style_history`.

## Подэтап 5
Подключить все режимы к единому orchestrator layer.

## Подэтап 6
Добавить сценарные тесты.

---

# 9. Архитектурный итог этапа

Этап 1 — это не "подготовка документации", а реальная фиксация предметной области.

После него проект должен перейти:
- от чат-бота с размытыми режимами
- к сценарию-ориентированной системе принятия решений.

Именно это создаёт основу для следующих этапов:
- тонкий frontend;
- orchestrator;
- обязательные generation jobs;
- анти-повтор;
- knowledge retrieval;
- масштабируемый ingestion pipeline;
- надёжная диагностика.
