
# Этап 12. Тестирование сценариев как продукта, а не только кода

## Контекст этапа

В основном архитектурном плане проекта Этап 12 сформулирован как переход к **тестированию сценариев как продукта, а не только кода**. В самом плане прямо указано, что нужны эталонные сценарии минимум по четырём режимам:
- 5 кейсов `general_advice`
- 5 кейсов `garment_matching`
- 5 кейсов `style_exploration`
- 5 кейсов `occasion_outfit`

Также в плане зафиксировано, что для каждого сценария нужно проверять:
- какой режим активирован;
- нужны ли уточнения;
- создалась ли generation job;
- дошёл ли prompt до Comfy;
- отличается ли результат от предыдущего.

К этому моменту архитектура проекта уже должна включать:
- Этап 0 — parser / ingestion pipeline как отдельный upstream процесс;
- Этап 1 — доменную модель и state machine;
- Этап 3 — explicit orchestrator;
- Этап 7 — новый structured prompt pipeline;
- Этап 8 — knowledge layer;
- Этап 9 — усиленный ComfyUI pipeline;
- Этап 10 — generation jobs и очереди;
- Этап 11 — observability и диагностику.

Следовательно, Этап 12 — это не “ещё один слой unit-тестов”, а **качество-контроль всей системы как пользовательского продукта**, где валидируется полный путь:
- parser / knowledge readiness;
- mode resolution;
- clarification behavior;
- prompt pipeline;
- generation jobs;
- Comfy execution;
- anti-repeat;
- финальное UX-поведение.

---

# 1. Цель этапа

Сделать так, чтобы качество системы оценивалось не только по тому:
- что тесты проходят;
- что код не падает;
- что worker не ломается;

а по тому:
- правильно ли система ведёт себя в реальных пользовательских сценариях;
- предсказуемо ли она завершает сценарий;
- создаёт ли generation там, где обязана;
- использует ли knowledge layer;
- сохраняет ли anti-repeat;
- выдаёт ли осмысленный и отличающийся результат.

После Stage 12 проект должен перейти от “мы собрали хорошую архитектуру” к “мы можем доказать, что продукт действительно работает как задумано”.

---

# 2. Почему обычных unit/integration тестов недостаточно

Даже при хорошем покрытии кода можно получить ситуацию, где:
- state machine корректна локально;
- orchestrator формально работает;
- prompt builder компилирует prompt;
- generation job создаётся;
- Comfy workflow отрабатывает;

но пользователь всё равно получает:
- не тот режим;
- лишние уточнения;
- одинаковые картинки;
- стилистически пустой ответ;
- несогласованный образ;
- отсутствие генерации в обязательном сценарии.

То есть продукт может быть “технически живым”, но “поведенчески плохим”.

Этап 12 нужен именно для того, чтобы тестировать **поведение всей системы как продукта**, а не только корректность отдельных модулей.

---

# 3. Главный принцип этапа

## Сценарий = first-class test object

После Stage 12 тестироваться должны не только:
- функции,
- сервисы,
- API endpoints,

а **эталонные сценарии пользователя**, которые проходят через всю архитектуру.

Базовый паттерн тестирования должен стать таким:

```text
Given:
  session context + user input + initial data state
When:
  user triggers command / sends message
Then:
  expected mode
  expected clarification behavior
  expected knowledge usage
  expected generation decision
  expected job lifecycle
  expected visual difference / semantic correctness
```

То есть сценарий становится отдельным артефактом продукта.

---

# 4. Связь Stage 12 с уже реализованными этапами

## 4.1. Связь с Этапом 0
Parser / ingestion pipeline уже существует и наполняет базу стилей. Значит сценарные тесты должны учитывать не только runtime, но и состояние данных:
- есть ли знание о стиле;
- свежи ли style records;
- достаточно ли заполнены traits, palette, garments, materials;
- как отсутствие или неполнота данных влияет на сценарий.

## 4.2. Связь с Этапом 1
Все сценарии должны проверять:
- какой `active_mode` в итоге установлен;
- корректен ли `flow_state`;
- не потерялся ли follow-up;
- сохранился ли `ChatModeContext`.

## 4.3. Связь с Этапом 3
Сценарные тесты должны валидировать `DecisionResult` как продуктовый контракт:
- `text_only`
- `clarification_required`
- `text_and_generate`
- `generation_only`
- `error_recoverable`

## 4.4. Связь с Этапами 4–6
Сценарии должны доказать, что:
- `garment_matching` действительно всегда переходит в generation при достаточном garment;
- `occasion_outfit` действительно работает как slot-filling flow;
- `style_exploration` реально не повторяет прошлый результат.

## 4.5. Связь с Этапами 7–9
Нужно тестировать:
- строится ли корректный `FashionBrief`;
- доходит ли knowledge bundle до prompt pipeline;
- доходит ли anti-repeat до Comfy layer;
- влияет ли mode-aware preset на финальную визуальную стратегию.

## 4.6. Связь с Этапом 10
Сценарный тест должен включать:
- создание generation job;
- корректный `job_id`;
- переходы статусов;
- получение результата через async path.

## 4.7. Связь с Этапом 11
Каждый сценарий должен быть traceable:
- есть `correlation_id`;
- есть полный execution trace;
- можно расследовать любой сбой сценария как продуктовый кейс.

---

# 5. Архитектурные принципы реализации

## 5.1. Clean Architecture

### Domain layer
Содержит:
- `ScenarioCase`
- `ScenarioExpectation`
- `ScenarioOutcome`
- `ScenarioFailure`
- `EvaluationDimension`

### Application layer
Содержит:
- `ScenarioTestRunner`
- `ScenarioEvaluator`
- `ScenarioDatasetBuilder`
- `ScenarioReplayService`
- `QualityGateService`

### Infrastructure layer
Содержит:
- fixtures/data loaders
- mock providers / test adapters
- generation result analyzers
- storage for scenario reports
- snapshot storage

### Interface layer
Содержит:
- admin/debug scenario runner
- report serializers
- diagnostics UI for scenario results

---

## 5.2. SOLID

### Single Responsibility
- scenario definition describes one product scenario;
- runner executes scenario;
- evaluator compares actual vs expected;
- reporter produces human-readable result;
- dataset builder prepares fixtures.

### Open/Closed
Новые режимы и новые scenario families должны добавляться через новые datasets и evaluators, а не через переписывание test framework.

### Liskov
Любой scenario runner должен быть заменяем:
- local synchronous runner
- queue-aware async runner
- replay runner
- CI runner

### Interface Segregation
Нужны отдельные интерфейсы:
- `ScenarioRepository`
- `ScenarioRunner`
- `ScenarioEvaluator`
- `ScenarioReporter`
- `ScenarioSnapshotStore`

### Dependency Inversion
Scenario testing layer зависит от абстракций runtime services, а не от конкретных production adapters.

---

## 5.3. FSD / модульная декомпозиция

Рекомендуемая структура:

```text
apps/backend/app/
  domain/
    scenario_testing/
      entities/
      enums/
      value_objects/
  application/
    scenario_testing/
      services/
        scenario_test_runner.py
        scenario_evaluator.py
        scenario_dataset_builder.py
        scenario_replay_service.py
        quality_gate_service.py
      use_cases/
        run_scenario_suite.py
        evaluate_scenario_result.py
        persist_scenario_report.py
  infrastructure/
    scenario_testing/
      fixtures/
      analyzers/
      snapshot_store/
      adapters/
  interfaces/
    api/
      admin/
      diagnostics/
      serializers/
```

---

# 6. Центральные сущности Stage 12

## 6.1. ScenarioCase

```python
class ScenarioCase(BaseModel):
    id: str
    mode: str
    title: str
    description: str
    preconditions: dict = {}
    input_messages: list[dict] = []
    expected: dict = {}
    tags: list[str] = []
```

### Что в него входит
- режим сценария;
- стартовое состояние сессии;
- входные сообщения;
- необходимые preloaded style / knowledge data;
- ожидания по mode / clarification / generation / anti-repeat.

---

## 6.2. ScenarioExpectation

```python
class ScenarioExpectation(BaseModel):
    expected_mode: str
    expected_decision_type: str
    clarification_required: bool = False
    clarification_count_max: int | None = None
    generation_required: bool = False
    knowledge_required: bool = False
    anti_repeat_required: bool = False
    expected_job_created: bool = False
    expected_result_differs_from_previous: bool = False
```

---

## 6.3. ScenarioOutcome

```python
class ScenarioOutcome(BaseModel):
    scenario_id: str
    actual_mode: str | None = None
    actual_decision_type: str | None = None
    clarification_count: int = 0
    generation_job_id: str | None = None
    prompt_hash: str | None = None
    knowledge_bundle_hash: str | None = None
    visual_preset_id: str | None = None
    passed: bool = False
    failures: list[str] = []
    traces: list[str] = []
```

---

# 7. Что именно Stage 12 тестирует

Этап 12 должен тестировать не “вообще всё подряд”, а конкретные продуктовые оси качества.

## 7.1. Mode correctness
- правильный ли режим активирован;
- не свалился ли follow-up в `general_advice`;
- не потерялся ли `ChatModeContext`.

## 7.2. Clarification behavior
- нужны ли уточнения;
- были ли они краткими и по делу;
- не было ли лишних уточнений;
- не было ли тишины после ответа пользователя.

## 7.3. Generation behavior
- создалась ли generation job, если она обязательна;
- не было ли ложного `text_only` там, где нужен `text_and_generate`;
- дошёл ли generation plan до worker.

## 7.4. Knowledge behavior
- использовался ли knowledge layer;
- был ли непустой `KnowledgeBundle`;
- соответствовал ли retrieval режиму сценария.

## 7.5. Prompt / visual behavior
- дошёл ли `FashionBrief` до prompt compiler;
- дошли ли diversity constraints до visual layer;
- был ли выбран корректный preset;
- отличается ли результат от предыдущего там, где это требуется.

## 7.6. Runtime behavior
- есть ли `job_id`;
- завершился ли async flow;
- есть ли статус и результат;
- нет ли silent failure.

---

# 8. Набор минимальных эталонных сценариев

Это напрямую следует из плана, но должно быть расширено с учётом уже выполненных этапов.

## 8.1. `general_advice` — минимум 5 кейсов

### Примеры:
1. нейтральный стилистический вопрос без генерации
2. follow-up уточнение без смены режима
3. запрос совета по сочетанию цветов
4. вопрос с исторической/теоретической окраской
5. текстовый совет, который не должен запускать generation

### Проверяем:
- mode correctness
- no accidental generation
- knowledge usage where relevant
- stable textual answer

---

## 8.2. `garment_matching` — минимум 5 кейсов

### Примеры:
1. точное описание вещи → сразу generation
2. слишком общее описание → одно уточнение → generation
3. текст + image asset → generation
4. edge case по материалу/формальности
5. повторный запрос в той же сессии

### Проверяем:
- активируется `garment_matching`
- не применяется 60 sec timeout как бизнес-логика
- `anchor_garment` построен
- generation обязательна при достаточных данных
- generation job реально создана

---

## 8.3. `style_exploration` — минимум 5 кейсов

### Примеры:
1. первый exploratory run
2. второй run с history
3. третий run с anti-repeat pressure
4. adjacent style family selection
5. exploratory mode с ограниченной knowledge coverage

### Проверяем:
- persistent `style_history`
- semantic diversity
- visual diversity
- anti-repeat дошёл до Comfy layer
- результат отличается от предыдущего

---

## 8.4. `occasion_outfit` — минимум 5 кейсов

### Примеры:
1. достаточный occasion context → immediate generation
2. неполный context → одно уточнение → generation
3. occasion с dress code
4. occasion с desired impression вместо dress code
5. edge case: ambiguous event type

### Проверяем:
- slot-filling behavior
- нет лишних уточнений
- нет тишины после follow-up
- generation обязательна при достаточном контексте

---

# 9. Сценарии должны учитывать parser / ingestion state

Это ключевая интеграция Stage 12 с Этапом 0.

## 9.1. Почему это важно
Если style knowledge уже живёт в БД и наполняется parser’ом, сценарий может ломаться не потому, что runtime плохой, а потому что:
- стиль не был наполнен;
- traits неполны;
- freshness низкая;
- style relations пустые.

## 9.2. Значит в scenario preconditions должно быть:
- какие style records должны существовать;
- какие поля knowledge layer должны быть заполнены;
- какой ingestion freshness допустим;
- допускается ли degraded mode при отсутствии данных.

## 9.3. Пример
Для `style_exploration` сценарий должен указывать:
- style X существует в style catalog
- у него есть palette, garments, materials
- есть related styles
- есть flatlay patterns / enough visual hints

Если чего-то нет — это фиксируется как data quality issue, а не как просто “LLM ответила плохо”.

---

# 10. Сценарное тестирование parser / knowledge readiness

Stage 12 должен включать не только runtime сценарии, но и readiness checks для базы знаний.

## 10.1. Что проверять
- для style ids, используемых в scenario suites, есть knowledge coverage;
- parser не оставил критические поля пустыми;
- freshness knowledge в допустимом диапазоне;
- extraction confidence не ниже порога.

## 10.2. Почему это часть Stage 12
Потому что продуктовый сценарий “style_exploration должен работать” зависит от качества данных parser’а.

---

# 11. Scenario runner architecture

## 11.1. Runner не должен быть просто pytest-скриптом
Нужен отдельный `ScenarioTestRunner`, который умеет:
- поднимать preconditions;
- запускать request sequence;
- ждать async generation jobs;
- собирать traces;
- валидировать expected outcomes;
- сохранять отчёт.

## 11.2. Контракт

```python
class ScenarioTestRunner(Protocol):
    async def run(self, scenario: ScenarioCase) -> ScenarioOutcome:
        ...
```

## 11.3. Важный момент
Runner должен быть queue-aware и observability-aware:
- ждать `job_id`;
- опрашивать статус;
- собирать `correlation_id`;
- вытягивать traces по сценарию.

---

# 12. Scenario evaluator

## 12.1. Зачем нужен отдельный evaluator
Проверка сценария не должна быть “один assert на HTTP status”.

Нужен evaluator, который сравнивает:
- actual mode vs expected mode
- actual decision vs expected decision
- clarification count vs allowed max
- job creation vs expected generation
- anti-repeat outcome vs required diversity
- knowledge usage vs expectation

## 12.2. Контракт

```python
class ScenarioEvaluator(Protocol):
    async def evaluate(
        self,
        scenario: ScenarioCase,
        outcome: ScenarioOutcome,
    ) -> list[str]:
        ...
```

---

# 13. Что значит "дошёл ли prompt до Comfy"

Это прямая часть Stage 12 по основному плану.

## 13.1. Проверка не должна быть поверхностной
Нужно валидировать:
- построен ли `FashionBrief`;
- построен ли compiled prompt;
- создан ли `VisualGenerationPlan`;
- создана ли generation job;
- picked ли job worker;
- вызван ли Comfy backend;
- сохранён ли result / failure.

## 13.2. То есть “prompt дошёл до Comfy” = целая цепочка
Не “есть ли строка prompt”, а:
- prompt built
- prompt persisted
- plan assembled
- plan queued
- worker consumed
- Comfy executed or failed explicitly

---

# 14. Что значит "отличается ли результат от предыдущего"

Это прямое продолжение Stage 6.

## 14.1. Проверка должна быть двухуровневой

### Semantic difference
- palette changed?
- hero garments changed?
- silhouette changed?
- materials changed?

### Visual difference
- preset changed?
- background changed?
- composition changed?
- camera distance changed?
- layout changed?

## 14.2. Почему это важно
Иначе anti-repeat будет протестирован слишком поверхностно.

---

# 15. Scenario snapshots и replay

## 15.1. Нужен snapshot store
Для каждого сценарного прогона полезно сохранять:
- input payloads
- traces
- knowledge bundle hash
- brief hash
- prompt hash
- generation job id
- result metadata
- optional thumbnails

## 15.2. Зачем
Это даёт:
- регрессионный анализ;
- replay проблемных кейсов;
- сравнение “до / после” изменений prompt builder или knowledge layer.

---

# 16. Quality gates

Stage 12 должен завершаться не только отчётом, но и **quality gates**.

## 16.1. Примеры quality gates
- `silent_failure_rate == 0` для эталонных сценариев
- `generation_required` сценарии всегда создают `job_id`
- `style_exploration` сценарии удовлетворяют minimum diversity threshold
- `occasion_outfit` не требует больше N уточнений
- `garment_matching` не возвращает `text_only` при достаточном garment

## 16.2. Зачем
Чтобы CI/CD и локальная разработка могли видеть не только “код не упал”, а “продуктовый контракт не нарушен”.

---

# 17. Сценарии как living product specification

## 17.1. Почему это важно
После Stage 12 эталонные сценарии должны выполнять роль:
- regression suite
- product contract
- acceptance criteria
- communication artifact между архитектурой и реализацией

## 17.2. Практически
Каждый новый режим, новый preset, новый retrieval strategy, новый workflow change должен проверяться через scenario suite.

---

# 18. Связь Stage 12 с observability из Этапа 11

Stage 11 дал:
- traces
- logs
- metrics
- silent failure detection

Stage 12 начинает использовать их как материал для оценки качества сценариев.

То есть:
- observability → data
- scenario testing → quality decision

Это важная логическая сцепка.

---

# 19. Роль frontend в Stage 12

Frontend не должен содержать логику тестирования, но product scenarios должны учитывать:
- async UX around `job_id`
- pending states
- successful result rendering
- error / recoverable error rendering
- отсутствие дублирования запросов

То есть часть сценариев должна тестировать ещё и UX-контракт:
- получил ли фронт `job_id`
- корректно ли дождался результата
- не пришлось ли пользователю повторно отправлять запрос

---

# 20. Рекомендуемая структура datasets

```text
infrastructure/scenario_testing/
  datasets/
    general_advice/
      scenario_01.yaml
      scenario_02.yaml
    garment_matching/
      scenario_01.yaml
      scenario_02.yaml
    style_exploration/
      scenario_01.yaml
      scenario_02.yaml
    occasion_outfit/
      scenario_01.yaml
      scenario_02.yaml
```

Где каждый сценарий содержит:
- preconditions
- input sequence
- expected outcomes
- data dependencies
- quality thresholds

---

# 21. Тестирование Stage 12

## 21.1. Unit tests
Покрыть:
- scenario parser / loader
- scenario evaluator
- quality gate service
- replay service
- diversity comparator
- scenario report builder

## 21.2. Integration tests
Покрыть:
- scenario runner against orchestrator
- scenario runner against generation queue
- scenario runner against retrieval layer
- scenario runner against parser readiness checks

## 21.3. E2E / acceptance tests
Покрыть:
- all 4 mode suites
- async generation completion
- anti-repeat validation
- fallback / recoverable error cases
- parser stale knowledge degradation cases

---

# 22. Рекомендуемая модульная структура

```text
domain/scenario_testing/
  entities/
    scenario_case.py
    scenario_expectation.py
    scenario_outcome.py
  value_objects/
    evaluation_dimension.py
    scenario_id.py

application/scenario_testing/
  services/
    scenario_test_runner.py
    scenario_evaluator.py
    scenario_dataset_builder.py
    scenario_replay_service.py
    quality_gate_service.py
  use_cases/
    run_scenario_suite.py
    evaluate_scenario_result.py
    persist_scenario_report.py

infrastructure/scenario_testing/
  fixtures/
  datasets/
  analyzers/
  snapshot_store/
  adapters/
```

---

# 23. Что не надо делать на этом этапе

Чтобы не разрушить идею Stage 12, нельзя:
- ограничиться unit-тестами сервисов;
- проверять только HTTP status и наличие JSON;
- не тестировать async generation path;
- не учитывать parser/knowledge readiness;
- не сравнивать anti-repeat по реальным результатам;
- считать, что “раз job создалась, значит сценарий успешен”;
- не вводить quality gates.

---

# 24. Пошаговый план реализации Этапа 12

## Подэтап 12.1. Ввести `ScenarioCase`, `ScenarioExpectation`, `ScenarioOutcome`
Создать центральные domain entities.

## Подэтап 12.2. Поднять scenario datasets по 4 режимам
Собрать минимум по 5 эталонных кейсов на каждый mode.

## Подэтап 12.3. Реализовать `ScenarioTestRunner`
Сделать runner, который проходит полный runtime path.

## Подэтап 12.4. Реализовать `ScenarioEvaluator`
Сравнивать actual outcome с product expectations.

## Подэтап 12.5. Добавить parser / knowledge readiness checks
Сделать data preconditions частью сценария.

## Подэтап 12.6. Добавить anti-repeat evaluators
Проверять semantic и visual diversity в `style_exploration`.

## Подэтап 12.7. Ввести `QualityGateService`
Сделать product-level pass/fail thresholds.

## Подэтап 12.8. Добавить replay, snapshot storage и отчёты
Сделать suite пригодным для регрессий и анализа.

---

# 25. Критерии готовности этапа

Этап 12 реализован корректно, если:

1. В проекте существуют эталонные сценарии по всем 4 режимам.
2. Сценарии проверяют не только код, но и продуктовый контракт поведения.
3. Для `garment_matching`, `style_exploration`, `occasion_outfit` проверяется обязательность generation.
4. Для `occasion_outfit` проверяется slot-filling behavior.
5. Для `style_exploration` проверяется anti-repeat на semantic и visual уровнях.
6. Для всех режимов проверяется отсутствие silent failure.
7. Scenario suite учитывает parser / knowledge readiness как часть качества.
8. Async generation path тестируется end-to-end.
9. Есть quality gates, блокирующие регрессию продукта.
10. Сценарии можно использовать как living specification системы.

---

# 26. Архитектурный итог этапа

После реализации Stage 12 проект получает то, чего обычно не хватает даже у хорошо спроектированных систем:
- не просто хорошую архитектуру,
- а **доказуемо корректное продуктовое поведение**.

Это завершает цепочку этапов 0–11:
- parser наполняет базу;
- knowledge layer использует её;
- orchestrator управляет сценариями;
- prompt builder и Comfy pipeline строят визуальный результат;
- queue layer делает runtime устойчивым;
- observability делает его прозрачным;
- scenario testing превращает всё это в продукт, который можно уверенно развивать без страха незаметно сломать ключевые пользовательские сценарии.
