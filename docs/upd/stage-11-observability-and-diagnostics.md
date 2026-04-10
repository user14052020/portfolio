
# Этап 11. Наблюдаемость и диагностика

## Контекст этапа

В основном архитектурном плане проекта Этап 11 сформулирован как обязательный слой **наблюдаемости и диагностики**. В плане прямо указано, что система уже слишком сложна, чтобы дебажить её "на ощущениях", и для каждого сообщения нужно писать:
- `session_id`
- `message_id`
- `requested_intent`
- `resolved_intent`
- `decision_type`
- `provider` (`vllm` / fallback)
- `generation_job_id`
- `prompt_hash`
- `style_id`
- `clarification_state`

Там же зафиксированы ключевые метрики:
- доля fallback-ответов;
- доля silent failure;
- доля генераций по режимам;
- среднее число уточнений до генерации;
- доля повторяющихся palette/signature items;
- успех парсинга стилей.

Важно, что к этому моменту проект уже имеет:
- Этап 0 — parser / ingestion pipeline как отдельный upstream процесс;
- Этап 3 — explicit orchestrator;
- Этап 7 — новый prompt pipeline;
- Этап 8 — knowledge layer;
- Этап 9 — усиленный ComfyUI pipeline;
- Этап 10 — generation jobs и очереди.

Следовательно, Этап 11 должен стать не “добавим логов”, а **единым observability layer**, который связывает:
- parser/ingestion,
- knowledge retrieval,
- orchestrator,
- prompt builder,
- generation queue,
- Comfy pipeline,
- frontend runtime UX.

---

# 1. Цель этапа

Сделать систему объяснимой и измеримой.

После Stage 11 ты должен уметь ответить на вопросы:

- почему бот дал именно такой ответ;
- где именно сломался путь конкретного сообщения;
- почему генерация не создалась;
- был ли использован knowledge layer;
- почему картинка повторилась;
- какой preset / workflow / prompt был применён;
- где parser теряет качество;
- как часто срабатывает fallback вместо основного reasoner;
- сколько уточнений обычно требуется до успешной генерации.

То есть Stage 11 превращает проект:
- из архитектурно хорошего, но opaque,
- в архитектурно хорошее и **операционно управляемое** решение.

---

# 2. Почему без observability остальные этапы не работают в полную силу

Даже если уже есть:
- state machine,
- orchestrator,
- slot-filling,
- anti-repeat,
- knowledge retrieval,
- Comfy presets,
- generation jobs,

без observability ты всё равно не знаешь:
1. где происходит регресс;
2. какой слой сломался;
3. что влияет на качество;
4. где bottleneck по latency;
5. где реально возникает “тишина”;
6. насколько parser/knowledge layer влияет на ответ и генерацию.

Основной план прямо говорит: систему нельзя дебажить “на ощущениях”. Это и есть сущность Этапа 11.

---

# 3. Архитектурный принцип этапа

## Observability — не инфраструктурная надстройка, а часть доменного execution flow

Это главный архитектурный принцип Stage 11.

То есть:
- логирование нельзя добавлять случайно по месту;
- метрики нельзя собирать “что получится”;
- traces не должны зависеть от конкретного слоя;
- observability должен быть встроен в application flow.

Идеальная цепочка выглядит так:

```text
Message received
→ route adapter
→ orchestrator
→ knowledge retrieval
→ fashion reasoning
→ prompt compilation
→ generation job creation
→ queue / worker execution
→ Comfy generation
→ result persistence
→ frontend delivery
```

И на каждом шаге:
- есть correlation id;
- есть typed event;
- есть traceable state transition;
- есть возможность реконструировать полный путь.

---

# 4. Связь с уже существующим parser / ingestion pipeline

Это обязательная поправка.

## 4.1. Parser уже существует как отдельный upstream процесс
Согласно Этапу 0, parser:
- наполняет базу стилей;
- нормализует и обогащает style data;
- пишет в БД;
- логирует источник и дату обновления.

Следовательно, observability layer Stage 11 должен охватывать не только chat runtime, но и ingestion runtime.

## 4.2. Это означает, что наблюдаемость должна быть двухконтурной

### Контур A — chat runtime observability
- intent resolution
- mode transitions
- knowledge retrieval
- prompt pipeline
- generation jobs
- Comfy execution

### Контур B — ingestion observability
- source fetch success
- normalization success
- extraction success
- style update success
- freshness / staleness
- source coverage

## 4.3. Почему это важно
Если quality в чате падает, проблема может быть:
- не в LLM;
- не в prompt builder;
- а в том, что parser не наполнил нужный стиль или наполнил его плохо.

Без Stage 11 это не видно.

---

# 5. Архитектурные принципы реализации

## 5.1. Clean Architecture

### Domain layer
Содержит:
- `TraceContext`
- `ObservationEvent`
- `ExecutionStage`
- `FailureType`
- `TelemetrySnapshot`
- value objects для `CorrelationId`, `PromptHash`, `KnowledgeBundleHash`, `GenerationJobId`

### Application layer
Содержит:
- `ObservabilityService`
- `EventEmitter`
- `TraceContextBuilder`
- `MetricsRecorder`
- `FailureClassifier`
- `ExecutionAuditService`

### Infrastructure layer
Содержит:
- structured logger
- metrics backend adapter
- tracing backend adapter
- log sinks
- dashboards / exporters
- storage for audit events

### Interface layer
Содержит:
- admin/debug endpoints
- trace viewers
- generation audit pages
- parser ingestion audit pages

---

## 5.2. SOLID

### Single Responsibility
- trace builder формирует correlation context;
- event emitter пишет typed events;
- metrics recorder публикует агрегаты;
- failure classifier определяет тип сбоя;
- audit service даёт удобное API для расследования.

### Open/Closed
Новый pipeline stage или новый worker type должен добавляться через новый event type / metric mapping, а не через переписывание всего observability слоя.

### Liskov
Любой sink должен быть взаимозаменяем:
- stdout json logger
- file sink
- ELK / OpenSearch
- OTEL collector

### Interface Segregation
Нужны отдельные интерфейсы:
- `StructuredLogger`
- `MetricsRecorder`
- `TracePublisher`
- `AuditRepository`

### Dependency Inversion
Application layer зависит от абстракций telemetry, а не от конкретного OpenTelemetry/Prometheus/Sentry stack.

---

## 5.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    observability/
      entities/
      enums/
      value_objects/
  application/
    observability/
      services/
        observability_service.py
        event_emitter.py
        metrics_recorder.py
        trace_context_builder.py
        execution_audit_service.py
      use_cases/
        emit_execution_event.py
        record_generation_metrics.py
        record_ingestion_metrics.py
  infrastructure/
    observability/
      logging/
      metrics/
      tracing/
      exporters/
      dashboards/
    persistence/
      audit/
  interfaces/
    api/
      admin/
      diagnostics/
      serializers/
```

---

# 6. Центральные сущности observability layer

## 6.1. TraceContext

```python
class TraceContext(BaseModel):
    correlation_id: str
    session_id: str | None = None
    message_id: str | None = None
    generation_job_id: str | None = None
    ingestion_job_id: str | None = None
    style_id: str | None = None
    mode: str | None = None
    created_at: datetime
```

### Зачем
Он связывает все события одного execution path между:
- API
- orchestrator
- retrieval
- prompt builder
- generation jobs
- workers
- parser jobs

---

## 6.2. ObservationEvent

```python
class ObservationEvent(BaseModel):
    correlation_id: str
    stage: str
    event_type: str
    severity: str = "info"
    payload: dict = {}
    created_at: datetime
```

### Примеры stages
- `api.request_received`
- `orchestrator.mode_resolved`
- `retrieval.bundle_built`
- `reasoning.brief_built`
- `prompt.compiled`
- `generation.job_enqueued`
- `generation.worker_started`
- `generation.completed`
- `generation.failed`
- `ingestion.source_fetched`
- `ingestion.normalized`
- `ingestion.persisted`

---

## 6.3. FailureType

```python
class FailureType(str, Enum):
    ROUTING_ERROR = "routing_error"
    KNOWLEDGE_RETRIEVAL_ERROR = "knowledge_retrieval_error"
    PROMPT_PIPELINE_ERROR = "prompt_pipeline_error"
    GENERATION_QUEUE_ERROR = "generation_queue_error"
    COMFY_EXECUTION_ERROR = "comfy_execution_error"
    INGESTION_FETCH_ERROR = "ingestion_fetch_error"
    INGESTION_NORMALIZATION_ERROR = "ingestion_normalization_error"
    SILENT_FAILURE = "silent_failure"
    FALLBACK_USED = "fallback_used"
```

### Почему
Stage 11 должен не просто логировать “что-то пошло не так”, а классифицировать сбои по слоям.

---

# 7. Сквозное логирование (end-to-end structured logging)

## 7.1. Что требует основной план
Основной план прямо перечисляет базовый набор полей для каждого сообщения:
- `session_id`
- `message_id`
- `requested_intent`
- `resolved_intent`
- `decision_type`
- `provider`
- `generation_job_id`
- `prompt_hash`
- `style_id`
- `clarification_state`

Это должно стать обязательным лог-контрактом.

## 7.2. Расширенный рекомендуемый лог-контракт

```python
{
  "correlation_id": "...",
  "session_id": "...",
  "message_id": "...",
  "requested_intent": "...",
  "resolved_intent": "...",
  "active_mode": "...",
  "decision_type": "...",
  "provider": "vllm|fallback",
  "knowledge_bundle_hash": "...",
  "fashion_brief_hash": "...",
  "prompt_hash": "...",
  "generation_job_id": "...",
  "style_id": "...",
  "visual_preset_id": "...",
  "clarification_state": "...",
  "created_at": "..."
}
```

## 7.3. Где логировать
Structured logging должно быть в:
- API route adapter
- orchestrator
- knowledge retrieval
- prompt builder
- generation scheduler
- worker executor
- parser/ingestion pipeline

---

# 8. Metrics layer

Stage 11 требует не только событийные логи, но и агрегируемые метрики.

## 8.1. Метрики chat runtime

### Метрики из плана
- доля fallback-ответов
- доля silent failure
- доля генераций по режимам
- среднее число уточнений до генерации
- доля повторяющихся palette/signature items

### Дополнительно рекомендовано
- mode resolution latency
- retrieval latency
- prompt build latency
- queue enqueue latency
- worker pickup latency
- generation duration
- prompt validation failure rate
- empty knowledge bundle rate

## 8.2. Метрики ingestion runtime

### Из плана
- успех парсинга стилей

### Расширяем до:
- source fetch success rate
- source empty response rate
- normalization success rate
- traits extraction success rate
- style upsert success rate
- average ingestion latency
- stale style ratio
- style coverage ratio

---

# 9. Stage-aware observability по слоям системы

## 9.1. Route / API layer
Что логировать:
- request received
- payload type
- requested intent
- client message id
- session id
- response type

## 9.2. Orchestrator layer
Что логировать:
- active mode before/after
- decision type
- clarification required?
- fallback used?
- reasoner chosen

## 9.3. Knowledge layer
Что логировать:
- query hash
- bundle hash
- retrieved groups
- cards count by group
- style_id hits
- empty bundle / partial bundle

## 9.4. Prompt pipeline
Что логировать:
- fashion brief built
- compiled prompt hash
- visual preset chosen
- validation passed / failed
- diversity constraints applied

## 9.5. Generation job layer
Что логировать:
- job created
- idempotency hit / miss
- queue selected
- worker picked
- status transition
- retry count
- failure class

## 9.6. ComfyUI layer
Что логировать:
- workflow selected
- prompt/negative prompt hashes
- seed
- visual preset
- result persisted
- execution duration
- provider/network errors

## 9.7. Ingestion layer
Что логировать:
- style source fetch
- parse/normalize/enrich/write
- source freshness
- source mismatch
- failed source attempts
- style update diff summary

---

# 10. Correlation / trace propagation

## 10.1. Почему это критично
Без correlation id нельзя связать:
- user message
- orchestrator decision
- knowledge bundle
- prompt hash
- generation job
- Comfy result
- parser freshness issues

## 10.2. Правило
Каждый user request должен получать `correlation_id`, который передаётся:
- в orchestrator;
- в knowledge retrieval;
- в prompt builder;
- в generation job metadata;
- в worker execution logs;
- в persisted result.

## 10.3. Для ingestion
У parser/ingestion тоже должен быть:
- `ingestion_run_id`
- `source_fetch_id`
- `style_record_id`

И link между `style_id` и chat/runtime traces.

---

# 11. Silent failure detection

Это один из ключевых пунктов плана.

## 11.1. Что считать silent failure
Silent failure — это любой кейс, когда:
- пользователь не получил ни текста, ни уточнения, ни `job_id`;
- generation не дошла до worker, но UI думает, что всё ок;
- prompt pipeline завершился без результата;
- follow-up потерялся между режимами;
- система ушла в fallback без фиксации.

## 11.2. Как это детектить
Нужны автоматические invariants:
- у каждого request есть terminal outcome:
  - `text_only`
  - `clarification_required`
  - `text_and_generate`
  - `generation_only`
  - `error_recoverable`
  - `error_hard`
- если terminal outcome отсутствует → `silent_failure`

## 11.3. Отдельная метрика
`silent_failure_rate` должен быть first-class metric.

---

# 12. Fallback observability

## 12.1. Почему это важно
В плане отдельно указана доля fallback-ответов.

Если система часто уходит в fallback:
- значит падает vLLM;
- или retrieval пуст;
- или prompt pipeline рушится;
- или worker architecture нестабильна.

## 12.2. Что логировать
Для каждого fallback:
- primary provider
- fallback provider
- reason
- mode
- quality_degradation_expected
- did_generation_continue

---

# 13. Replay и forensic debugging

Stage 11 должен сделать возможным повторный разбор проблемного кейса.

## 13.1. Что нужно сохранять для replay
- user message
- resolved mode
- knowledge bundle hash / optional snapshot
- fashion brief
- compiled prompt
- visual preset
- generation plan
- workflow name
- seed
- result metadata

## 13.2. Почему это важно
Без replay нельзя расследовать:
- почему получилась повторяющаяся картинка;
- почему образ не соответствует occasion;
- почему anchor garment потерялся;
- почему fallback сработал.

---

# 14. Admin / diagnostics UX

## 14.1. Нужны внутренние диагностические views
Даже если это не публичная фича, для поддержки проекта полезны:
- trace viewer by `correlation_id`
- generation job inspector by `job_id`
- knowledge bundle preview
- prompt pipeline preview
- style ingestion audit page

## 14.2. Что должно быть видно
- mode
- decision type
- knowledge refs
- prompt hashes
- preset
- workflow
- failures / retries
- parser freshness по `style_id`

---

# 15. Parser observability как часть Stage 11

Это ключевая интеграция с Этапом 0.

## 15.1. Что нужно видеть по parser/ingestion
- какие стили давно не обновлялись;
- по каким стилям source fetch unstable;
- какие records incomplete;
- какие traits extraction failed;
- какие style relations missing.

## 15.2. Почему это важно для chat runtime
Если style knowledge для нужного стиля устарела или неполна:
- `style_exploration` деградирует;
- `garment_matching` становится generic;
- `occasion_outfit` теряет specificity.

То есть parser observability прямо влияет на качество чата.

---

# 16. Metrics dashboard design

## 16.1. Чатовый дашборд
Отдельный dashboard должен показывать:
- requests by mode
- decision types by mode
- clarification count
- fallback rate
- silent failure rate
- generation job success
- average generation latency
- repeat indicators

## 16.2. Ingestion dashboard
Отдельный dashboard должен показывать:
- styles fetched today
- styles updated successfully
- failed source fetches
- empty-body fetches
- style freshness distribution
- extraction coverage

## 16.3. Why separate dashboards
Потому что chat runtime и ingestion runtime — это связанные, но разные контуры.

---

# 17. Alerting strategy

## 17.1. Что должно алертить
- резкий рост `silent_failure_rate`
- рост `fallback_rate`
- рост queue latency
- падение generation success rate
- рост parser empty response rate
- рост stale style ratio

## 17.2. Почему alerting — часть Stage 11
Потому что observability без реакции превращается в “мы просто красиво логируем деградацию”.

---

# 18. Storage strategy for audit events

## 18.1. Что хранить краткосрочно
- full structured logs
- generation traces
- worker events

## 18.2. Что хранить долговременно
- aggregates
- failures
- job summaries
- parser audit summaries
- prompt hashes and metadata

## 18.3. Почему не хранить всё вечно
Потому что observability должна быть полезной, а не превращаться в бесконтрольную свалку событий.

---

# 19. Тестирование observability

## 19.1. Unit tests
Покрыть:
- trace context builder
- failure classifier
- metrics recorder
- event schemas
- silent failure detector

## 19.2. Integration tests
Покрыть:
- request -> full trace emitted
- generation job -> status transitions logged
- fallback path -> metrics incremented
- parser run -> ingestion events recorded
- missing terminal outcome -> silent failure detected

## 19.3. E2E сценарии
Минимальный набор:
1. normal `garment_matching` path emits full trace
2. `style_exploration` repeat emits anti-repeat metrics
3. `occasion_outfit` clarification flow logs slot transitions
4. generation failure classified correctly
5. parser failure surfaces in ingestion dashboard

---

# 20. Рекомендуемая модульная структура

```text
domain/observability/
  entities/
    trace_context.py
    observation_event.py
    telemetry_snapshot.py
  enums/
    execution_stage.py
    failure_type.py
  value_objects/
    correlation_id.py
    prompt_hash.py
    knowledge_bundle_hash.py

application/observability/
  services/
    observability_service.py
    event_emitter.py
    metrics_recorder.py
    trace_context_builder.py
    execution_audit_service.py
  use_cases/
    emit_execution_event.py
    record_generation_metrics.py
    record_ingestion_metrics.py
    detect_silent_failure.py

infrastructure/observability/
  logging/
    structured_logger.py
  metrics/
    metrics_backend_adapter.py
  tracing/
    trace_publisher.py
  exporters/
    otel_exporter.py
  dashboards/
    chat_runtime_dashboard.md
    ingestion_dashboard.md
```

---

# 21. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- логировать только ad hoc print-ами;
- собирать метрики только на уровне HTTP route;
- игнорировать ingestion observability;
- не связывать generation job traces с user message;
- не различать fallback и hard failure;
- оставлять silent failure без явного detector;
- считать observability внешней “ops-задачей”, не связанной с продуктовой архитектурой.

---

# 22. Пошаговый план реализации Этапа 11

## Подэтап 11.1. Ввести `TraceContext` и `ObservationEvent`
Создать центральные сущности observability layer.

## Подэтап 11.2. Встроить correlation id во все runtime paths
API → orchestrator → retrieval → prompt → jobs → worker → result.

## Подэтап 11.3. Реализовать structured logging
Единый обязательный лог-контракт для chat runtime.

## Подэтап 11.4. Реализовать metrics layer
Собрать ключевые продуктовые и технические метрики.

## Подэтап 11.5. Реализовать silent failure detector
Формализовать отсутствие terminal outcome как отдельный тип сбоя.

## Подэтап 11.6. Подключить ingestion observability
Сделать parser/knowledge freshness видимой в общей системе.

## Подэтап 11.7. Добавить admin/debug diagnostics
Trace viewer, job inspector, ingestion audit.

## Подэтап 11.8. Добавить alerting и тесты
Сделать observability действительно operationally useful.

---

# 23. Критерии готовности этапа

Этап 11 реализован корректно, если:

1. У каждого user request есть `correlation_id`.
2. Логи связывают request, orchestrator, retrieval, prompt, generation job и result.
3. `silent_failure_rate` измеряется как first-class metric.
4. `fallback_rate` измеряется и объясняется.
5. Generation jobs имеют полную lifecycle observability.
6. Ingestion/parser тоже включён в общую систему наблюдаемости.
7. По `style_id` можно увидеть связь между parser freshness и chat quality.
8. Существуют debug/admin инструменты для расследования.
9. Система покрыта observability unit / integration / e2e тестами.
10. Основные продуктовые и технические регрессии больше не ищутся “на ощущениях”.

---

# 24. Архитектурный итог этапа

После реализации Этапа 11 проект получает полноценный слой **операционной прозрачности**:

- chat runtime становится traceable;
- orchestrator перестаёт быть “чёрным ящиком”;
- retrieval, prompt builder, Comfy pipeline и jobs становятся измеримыми;
- parser/ingestion встраивается в единую диагностическую картину;
- silent failures и fallback становятся видимыми;
- любые дальнейшие улучшения можно делать на основе данных, а не догадок.

Именно Stage 11 превращает всю предыдущую архитектуру — от parser до generation queue — в систему, которую можно не только строить, но и уверенно сопровождать, масштабировать и улучшать.
