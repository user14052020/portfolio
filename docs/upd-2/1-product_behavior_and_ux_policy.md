
# Этап 1. Product behavior and UX policy  
## Подробный план реализации продуктового поведения и UX-политики fashion chatbot

## 0. Назначение документа

Этот документ выделяет и детализирует первый implementation block из общего master-плана переработки fashion chatbot. Его задача — зафиксировать **новое поведение продукта**, **правила UX**, **политику запуска генерации**, **управление режимами**, а также **архитектурные границы**, которые обеспечат чистую и поддерживаемую реализацию. Общий master-план уже зафиксировал, что система должна перейти от “генератора картинок” к **fashion reasoning assistant**, который сначала помогает текстом, а визуализацию запускает только по осознанному триггеру. fileciteturn7file0

Документ описывает:
- какую продуктовую модель нужно внедрить;
- как должна вести себя система в каждом типе пользовательского взаимодействия;
- какие компоненты должны появиться в backend и frontend;
- какие изменения нужно внести в текущее управление режимами;
- какие UX-сценарии допустимы и какие запрещены;
- как зафиксировать новое поведение как устойчивый контракт системы.

---

# 1. Контекст и причина этапа

На текущем состоянии проекта реализованы этапы 0–9 общего плана, но в продукте сохраняется критическая проблема: бот слишком часто трактует диалог как генерационный сценарий. В результате свободный ввод пользователя начинает вести к необоснованному запуску изображения. Это ломает базовую модель взаимодействия и делает бота тяжёлым, непредсказуемым и дорогим в эксплуатации. Master-plan уже зафиксировал, что по умолчанию бот должен **разговаривать и советовать**, а визуализация должна запускаться только по явному триггеру. fileciteturn7file0

Следовательно, этот этап — не “косметическая правка кнопок”, а **продуктово-архитектурная стабилизация поведения всей системы**.

---

# 2. Цель этапа

После реализации этого этапа продукт должен работать по следующему базовому правилу:

1. Пользователь пишет сообщение.
2. Бот по умолчанию отвечает текстом как умный стилист.
3. Если визуализация действительно уместна, бот предлагает её как отдельный следующий шаг.
4. Генерация запускается:
   - либо по кнопке `Попробовать другой стиль`;
   - либо по явному текстовому запросу пользователя на визуализацию;
   - либо после явного подтверждения CTA.

Эта логика должна быть реализована как **доменная политика продукта**, а не как набор разрозненных if-ов в обработчиках.

---

# 3. Новый продуктовый принцип

## 3.1. Продуктовая формулировка

Бот должен быть переосмыслен как:

> **fashion reasoning assistant**, который:
- объясняет;
- предлагает;
- уточняет;
- помогает подобрать;
- стилизует;
- исторически и композиционно обосновывает решение;
- визуализирует только по запросу.

Именно это означает переход от image-first логики к **conversation-first** и **reasoning-first** модели. Такой принцип уже зафиксирован в общем плане и здесь становится первым обязательным продуктовым контрактом. fileciteturn7file0

---

## 3.2. Что это означает practically

Это означает, что сообщение пользователя:
- не должно считаться generation command по умолчанию;
- не должно автоматически наследовать generation mode из прошлого сценария;
- не должно запускать изображение только потому, что раньше пользователь уже взаимодействовал с visual flow.

Таким образом, продуктовое поведение должно быть переопределено так:

```text
DEFAULT = text interaction
GENERATION = explicit action
```

---

# 4. Главная текущая проблема: sticky generation mode

## 4.1. Наблюдаемое поведение

Из общего плана следует, что сейчас generation-oriented режим “залипает” после visual-сценариев, особенно после `style_exploration`. Практически это проявляется так:

1. пользователь нажимает `Попробовать другой стиль`;
2. бот генерирует образ;
3. пользователь пишет что-то вне visual-сценария, например `привет`;
4. система продолжает трактовать контекст как generation-capable flow;
5. запускается ещё одна генерация или generation-oriented логика.

Это является прямым нарушением нового продуктового принципа. fileciteturn7file0

---

## 4.2. Архитектурный смысл проблемы

Проблема не в конкретном тексте пользователя и не в prompt-компиляции, а в том, что:
- нет жёстко зафиксированной policy layer для generation;
- нет обязательного post-generation reset;
- mode lifecycle не замкнут;
- visual mode перетекает в обычный диалог.

Следовательно, исправление должно быть сосредоточено на:
- state lifecycle;
- generation policy;
- post-action mode transition.

---

# 5. Базовая UX policy

## 5.1. Text-first как единственно допустимый default

Новая UX-политика должна зафиксировать:

### По умолчанию:
- бот отвечает **только текстом**;
- генерация не запускается;
- UI не ведёт пользователя в visual branch без триггера.

### Генерация допустима только если:
- пользователь нажал `Попробовать другой стиль`;
- пользователь явно попросил визуализацию;
- бот предложил CTA, и пользователь согласился.

Это правило должно быть зафиксировано как:
- доменная политика;
- backend policy service;
- frontend interaction contract.

---

## 5.2. Зачем это нужно

Это даёт:
- предсказуемый UX;
- более естественный разговор;
- меньшую нагрузку на ComfyUI и очереди;
- меньшую нагрузку на vLLM reasoning pipeline;
- чистую продуктовую модель;
- лучшее соответствие роли “умного стилиста”, а не “машины, которая на всё рисует картинку”.

---

# 6. Политика кнопок и быстрых сценариев

## 6.1. Что должно быть удалено

Из интерфейса должны быть убраны:
- `Подобрать к вещи`
- `Что надеть на событие`

Master-plan уже фиксирует, что эти сценарии лучше обрабатываются естественным языком, а не жёсткими кнопочными ветками. fileciteturn7file0

---

## 6.2. Что должно остаться

Остаётся только одна кнопка:

- `Попробовать другой стиль`

---

## 6.3. Почему это архитектурно правильно

Потому что:
- `garment_matching` и `occasion_outfit` должны стать естественными conversational scenarios;
- кнопки для них создают ложное ощущение, что visual mode — основной;
- чем меньше жёстких shortcut branches, тем проще поддержка mode lifecycle;
- одна visual-кнопка проще для пользователя и чище для state machine.

---

# 7. Новая модель пользовательских сценариев

## 7.1. General advice scenario

Это основной сценарий продукта.

### Характеристики:
- default mode
- text-only by default
- generation выключен
- focus на reasoning и advice

### Примеры запросов:
- “Привет”
- “Что сейчас выглядит интеллектуально, но не скучно?”
- “Как носить серое пальто?”
- “Что можно собрать на вечернюю выставку?”

### Ожидаемое поведение:
- бот отвечает текстом;
- если уместно — предлагает CTA на визуализацию;
- без CTA и без явного запроса generation не запускается.

---

## 7.2. Style exploration scenario

Это единственный сценарий, где визуализация запускается как основной продуктовый результат.

### Характеристики:
- запускается по кнопке `Попробовать другой стиль`
- допускает text + generation
- обязан поддерживать anti-repeat
- после завершения должен быть reset в `general_advice`

### Ожидаемое поведение:
1. кнопка нажата
2. бот может дать короткую стилевую подводку
3. запускается generation
4. после сохранения результата visual-mode считается завершённым
5. последующий свободный ввод не должен наследовать generation

---

## 7.3. Garment / occasion conversational scenarios

Эти сценарии больше не должны быть кнопочными.

### Характеристики:
- инициируются естественной фразой пользователя;
- сначала проходят через text reasoning;
- generation возможен только при explicit visual intent или через CTA;
- должны ощущаться как нормальный диалог со стилистом.

### Примеры:
- “У меня серое пальто, с чем носить?”
- “Что надеть на выставку вечером?”
- “Хочу мягкий интеллектуальный образ”

---

# 8. CTA (Call-to-Action) как продуктовый мост между текстом и генерацией

## 8.1. Зачем нужен CTA

CTA позволяет не превращать текстовый совет сразу в image-generation branch, а сделать визуализацию **вторым осознанным шагом**. Это продуктово чище и архитектурно полезнее, потому что разрывает прямую связь:

```text
user_message -> generation
```

и заменяет её на:

```text
user_message -> advice -> CTA -> user confirmation -> generation
```

---

## 8.2. Новый UX-контракт

Backend должен уметь возвращать:

- основной текст ответа;
- флаг `can_offer_visualization`;
- текст CTA;
- тип предложенной визуализации.

Пример response DTO:

```json
{
  "text": "Для выставки я бы собрал вытянутый образ с мягким верхом и сдержанным контрастом.",
  "can_offer_visualization": true,
  "cta_text": "Собрать flat lay референс?"
}
```

---

## 8.3. Frontend behavior

Если `can_offer_visualization = true`, frontend должен:
- показать CTA-кнопку;
- не запускать generation автоматически;
- при клике отправить отдельный explicit visual action.

---

# 9. Generation policy как отдельный доменный слой

## 9.1. Почему это нельзя оставлять в handlers

Если generation decision размазан по обработчикам, ты получаешь:
- дублирование логики;
- скрытые side effects;
- сложность тестирования;
- невозможность быстро зафиксировать единое поведение;
- рост хаоса при добавлении новых сценариев.

Следовательно, generation должен решаться централизованно.

---

## 9.2. Новый компонент: `GenerationPolicyService`

Нужен отдельный сервис, отвечающий только за один вопрос:

> должен ли текущий запрос приводить к генерации изображения?

### Его задача:
- принимать контекст запроса;
- учитывать текущий mode;
- учитывать UI action;
- учитывать generation intent;
- учитывать пост-сценарный reset;
- вернуть явное decision object.

---

## 9.3. Рекомендуемый контракт

```python
class GenerationDecision:
    should_generate: bool
    reason: str
    should_offer_cta: bool
    cta_text: str | None
```

```python
class GenerationPolicyService(Protocol):
    async def decide(self, context: GenerationPolicyInput) -> GenerationDecision:
        ...
```

---

## 9.4. Принципы SOLID здесь

### SRP
Сервис отвечает только за policy decision, а не за вызов ComfyUI или сбор prompt.

### OCP
Новые product rules добавляются через новые policy rules, а не переписывают handlers.

### DIP
Orchestrator зависит от интерфейса policy service, а не от конкретной реализации.

---

# 10. Политика reset после visual scenario

## 10.1. Обязательное правило

После завершённого `style_exploration` или любого explicit visual flow система должна по умолчанию возвращаться в `general_advice`.

---

## 10.2. Условие reset

Reset должен происходить если:
- visual job завершён;
- нет pending clarification / slot-filling;
- нет explicit “ещё один визуальный вариант”;
- нет активного продолжения того же generation flow.

---

## 10.3. Рекомендуемая доменная политика

```python
if generation_completed and not has_active_followup:
    active_mode = GENERAL_ADVICE
    should_auto_generate = False
    pending_flow_state = IDLE
```

---

## 10.4. Где это должно жить

Не в UI, не в Comfy integration и не в отдельных handler’ах.

Это должно жить в:
- `ConversationStatePolicy`
- `SessionFlowStateService`
- `OrchestratorPostActionPolicy`

---

# 11. LocalStorage и frontend interaction state

## 11.1. Что должен хранить frontend

Для UX policy достаточно ввести простой client-side interaction state:
- `last_user_action_type`
- `last_visual_cta_shown`
- `last_visual_cta_confirmed`
- `presentation_profile` и связанные preference values

Это позволит:
- не показывать лишний CTA повторно;
- не запускать generation повторно из старого UI-состояния;
- сохранять мягкий user profile.

---

## 11.2. Важно
Frontend не должен самостоятельно “решать”, можно ли генерировать.  
Он должен только:
- хранить interaction hints;
- отправлять explicit actions;
- отображать CTA.

Решение принимает backend policy layer.

---

# 12. Role of backend vs frontend

## 12.1. Frontend отвечает за
- отрисовку кнопок и CTA;
- сбор explicit visual action;
- хранение локальных hints;
- отображение transition states.

## 12.2. Backend отвечает за
- доменную policy;
- mode lifecycle;
- generation decision;
- reset behavior;
- orchestration;
- consistency between text and generation branches.

---

# 13. Что должно быть запрещено после этого этапа

Нельзя допускать следующие паттерны:

- generation по умолчанию на любой non-general mode;
- generation из старого mode без нового user trigger;
- запуск generation напрямую из handler’а без policy layer;
- повторный generation только потому, что раньше был visual scenario;
- UI, который запускает generation без явного подтверждения.

Это должно быть зафиксировано как technical guardrails.

---

# 14. Clean Architecture и модульная раскладка

## 14.1. Domain layer

Нужно ввести или зафиксировать:
- `GenerationDecision`
- `ConversationModePolicy`
- `PostGenerationResetRule`
- `VisualizationOffer`

Это должны быть доменные сущности или policy objects, а не ad hoc dicts.

---

## 14.2. Application layer

Новые или переработанные сервисы:
- `GenerationPolicyService`
- `ConversationStatePolicy`
- `SessionFlowStateService`
- `PostActionConversationPolicy`

Они должны координировать product behavior.

---

## 14.3. Interface layer

Нужно адаптировать:
- response DTO для чата
- explicit visual CTA action endpoint
- frontend contracts для quick actions

---

## 14.4. Infrastructure layer

Сюда не должна утекать продуктовая логика.  
Infra only:
- persistence
- ComfyUI adapter
- message transport
- queue interaction

Policy решения не должны жить здесь.

---

# 15. FSD-подход для frontend

Для frontend логика должна быть разложена так, чтобы UX-политика не была размазана по компонентам.

## Рекомендуемые блоки:
- `entities/chat`
- `entities/profile`
- `features/chat-send-message`
- `features/chat-request-visualization`
- `features/chat-quick-actions`
- `features/profile-context`
- `widgets/chat-panel`

Главное:
- кнопка `Попробовать другой стиль` — это feature;
- CTA визуализации — отдельная feature;
- presentation profile — отдельная entity/feature.

---

# 16. OOP / SOLID ориентиры реализации

## 16.1. Не смешивать роли классов
- Router не должен решать generation policy.
- Policy service не должен собирать prompt.
- Prompt builder не должен сбрасывать mode.
- UI adapter не должен менять доменный state.

## 16.2. Открытость к расширению
Новая visual policy в будущем должна добавляться через новые decision rules, а не через переписывание всех handlers.

## 16.3. Явные контракты
Все продуктовые решения должны быть представлены явными типами:
- не “магические bool’ы”;
- не скрытые side effects;
- не неявная логика в if-цепочках.

---

# 17. Пошаговый план реализации

## Подэтап 1. Зафиксировать новый UX contract
- Описать response DTO для text-first + CTA
- Описать explicit visual request DTO
- Зафиксировать единственную quick action: `Попробовать другой стиль`

## Подэтап 2. Удалить старые quick actions
- убрать `Подобрать к вещи`
- убрать `Что надеть на событие`
- удалить связанную UI-логику и старые прямые generation shortcuts

## Подэтап 3. Ввести `GenerationPolicyService`
- централизовать generation decision
- запретить implicit generation по mode alone
- сделать text-first default

## Подэтап 4. Ввести reset policy после generation
- реализовать reset в state lifecycle
- убрать sticky visual mode

## Подэтап 5. Реализовать CTA-поток
- backend возвращает `can_offer_visualization`
- frontend показывает CTA
- explicit confirm отправляет отдельный action

## Подэтап 6. Обновить acceptance tests
- `привет` никогда не должен вызывать generation
- post-generation free text должен идти в `general_advice`
- без explicit trigger generation невозможен

---

# 18. Acceptance criteria

Этот этап считается завершённым, если:

1. Сообщение `привет` не запускает generation.
2. Любой свободный ввод после завершённого `style_exploration` не запускает generation автоматически.
3. В интерфейсе остаётся только кнопка `Попробовать другой стиль`.
4. Garment/occasion запросы по умолчанию начинают текстовый сценарий.
5. Генерация запускается только по:
   - кнопке,
   - explicit visual request,
   - подтверждённому CTA.
6. Generation policy вынесен в отдельный сервис.
7. Reset visual-mode реализован централизованно, а не в отдельных handlers.
8. Frontend не принимает самостоятельных product decisions о generation.
9. В response contract есть поддержка CTA.
10. Поведение покрыто product-level tests.

---

# 19. Definition of Done

Этап реализован корректно, если:

- бот стал text-first по умолчанию;
- visual generation стала осознанным вторым шагом;
- генерация больше не “залипает” в последующих сообщениях;
- UX стал проще и естественнее;
- архитектурно product behavior вынесен в отдельный policy layer;
- дальнейшее добавление semantic routing и knowledge layers можно делать без ломки базового UX.

---

# 20. Архитектурный итог этапа

После реализации этого документа система перестаёт быть “визуальным автоматом”, который слишком часто уходит в generation branch. Она становится:
- conversation-first,
- controllable,
- extendable,
- product-safe.

И самое главное — создаётся стабильный фундамент для следующих implementation blocks:
- semantic routing через vLLM,
- FashionReasoner,
- profile context,
- future editorial knowledge providers,
- persona / voice composition.

Этот этап должен быть реализован первым, потому что без него все дальнейшие улучшения будут надстраиваться на нестабильное продуктовое поведение.
