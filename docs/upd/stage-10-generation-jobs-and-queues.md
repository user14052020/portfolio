
# Этап 10. Ввести generation jobs и очереди как обязательный слой

## Контекст этапа

В основном архитектурном плане проекта Этап 10 сформулирован однозначно: генерацию изображения нельзя держать как длинный синхронный HTTP-сценарий. В плане прямо указано, что нужен отдельный **job queue layer**, например `Redis + RQ / Celery`, отдельный worker для image generation и отдельный worker для style ingestion. Там же зафиксирован целевой flow:

- API route принимает сообщение;
- orchestrator принимает решение;
- если нужна генерация — создаётся job;
- frontend получает `job_id`;
- дальше polling / websocket / SSE;
- когда job завершилась — UI подтягивает результат.

Это нужно для устойчивости:
- без таймаутов;
- без двойных кликов;
- без подвисаний запроса.

Критически важно, что у проекта уже есть **Этап 0** — parser / ingestion pipeline, который живёт как отдельный upstream-процесс и наполняет базу стилей подробными данными. Значит Stage 10 должен строиться не как “очередь только для картинок”, а как **единый runtime pattern**, который:
- не смешивает chat API и тяжёлую генерацию;
- допускает отдельные worker types;
- логически совместим с уже существующим ingestion worker;
- связывает orchestrator, knowledge layer, prompt builder и ComfyUI в устойчивую execution-модель.

---

# 1. Цель этапа

Перевести runtime проекта от модели:

```text
HTTP request
→ heavy reasoning
→ heavy prompt build
→ heavy image generation
→ wait
→ timeout / duplicate / freeze
```

к модели:

```text
HTTP request
→ orchestrator
→ typed decision
→ enqueue generation job
→ immediate response with job_id
→ worker executes job
→ result persisted
→ frontend subscribes / polls
```

После Stage 10 система должна:
- устойчиво переживать долгие генерации;
- не блокировать request/response цикл;
- исключать double-submit и accidental duplicate jobs;
- обеспечивать воспроизводимость generation;
- быть масштабируемой по workers;
- быть совместимой с уже существующим parser/ingestion слоем.

---

# 2. Архитектурная проблема синхронной генерации

Если generation остаётся синхронной частью API-запроса, появляются системные дефекты:

1. **HTTP timeout**
   - generation в Comfy и тяжёлый pipeline могут занимать десятки секунд и больше.

2. **silent failure**
   - часть pipeline отрабатывает, но frontend не получает предсказуемый результат.

3. **дубли generation**
   - пользователь нажимает повторно, потому что не видит status.

4. **хрупкость к инфраструктурным сбоям**
   - падение Comfy, перегрузка GPU, сетевой timeout ломают весь request.

5. **невозможность нормального scaling**
   - API server вынужден ждать тяжёлую работу.

6. **плохая наблюдаемость**
   - сложно понять, на каком именно шаге сломался путь.

Основной план Stage 10 как раз и закрывает эти проблемы через queue/job architecture.

---

# 3. Ключевой архитектурный принцип

## Runtime должен быть разделён на 3 слоя исполнения

### 1. API / request layer
Принимает сообщения, вызывает orchestrator и возвращает быстрый typed response.

### 2. Orchestration / job creation layer
Решает:
- нужен ли generation job;
- какой generation plan собрать;
- какой worker queue выбрать;
- какой idempotency key использовать.

### 3. Worker execution layer
Реально выполняет:
- image generation
- media persistence
- metadata persistence
- status transitions
- retry / failure handling

---

# 4. Связь Stage 10 с уже существующим ingestion pipeline

Это обязательная поправка к архитектуре.

## 4.1. Parser уже живёт как отдельный процесс
Согласно Этапу 0, parser:
- не живёт внутри chat backend;
- работает как отдельный ingestion pipeline / cron / worker;
- наполняет базу стилей;
- логирует источники и дату обновления.

Следовательно, Stage 10 должен **не создавать вторую несвязанную модель worker-ов**, а вводить единый runtime pattern:

```text
chat runtime jobs
+
style ingestion jobs
=
единая job-driven архитектура проекта
```

## 4.2. Практический вывод
После Stage 10 проект должен мыслиться так:
- parser/ingestion worker — upstream data acquisition worker
- image generation worker — downstream visual execution worker
- возможно позже:
  - enrichment worker
  - cleanup worker
  - re-ranking worker
  - observability/reporting worker

То есть queue layer — это не только про картинки, а про нормальный execution backbone всего проекта.

---

# 5. Архитектурные принципы реализации

## 5.1. Clean Architecture

### Domain layer
Содержит:
- `GenerationJob`
- `GenerationJobStatus`
- `GenerationRequest`
- `GenerationResult`
- `GenerationFailure`
- `JobRetryPolicy`
- `JobIdempotencyKey`

### Application layer
Содержит:
- `GenerationJobScheduler`
- `GenerationJobService`
- `GenerationStatusService`
- `CreateGenerationJobUseCase`
- `ExecuteGenerationJobUseCase`
- `PersistGenerationResultUseCase`

### Infrastructure layer
Содержит:
- Redis / queue backend
- RQ / Celery adapter
- worker implementations
- Comfy adapter
- media storage adapter
- DB repositories for jobs/results

### Interface layer
Содержит:
- API endpoints:
  - create chat response
  - get job status
  - get job result
- websocket / SSE / polling serializers

---

## 5.2. SOLID

### Single Responsibility
- orchestrator решает, что generation нужна;
- scheduler ставит job в очередь;
- worker исполняет job;
- status service читает job state;
- result persistence сохраняет результат и metadata.

### Open/Closed
Новые типы jobs должны добавляться без переписывания общей queue architecture:
- image_generation_job
- style_ingestion_job
- style_enrichment_job
- knowledge_reindex_job

### Liskov
Любой queue adapter должен быть заменяем по интерфейсу:
- `RQGenerationQueue`
- `CeleryGenerationQueue`
- `InMemoryQueueForTests`

### Interface Segregation
Нужны отдельные интерфейсы:
- `GenerationJobScheduler`
- `GenerationJobRepository`
- `GenerationResultRepository`
- `GenerationWorkerExecutor`
- `JobStatusPublisher`

### Dependency Inversion
Application layer зависит от очереди и persistence через абстракции, а не от конкретного Redis/RQ/Celery.

---

## 5.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    generation_jobs/
      entities/
      enums/
      value_objects/
      policies/
  application/
    generation_jobs/
      services/
        generation_job_service.py
        generation_status_service.py
        generation_result_service.py
      use_cases/
        create_generation_job.py
        execute_generation_job.py
        complete_generation_job.py
        fail_generation_job.py
  infrastructure/
    queue/
      adapters/
      workers/
      schedulers/
    comfy/
    storage/
    persistence/
  interfaces/
    api/
      routes/
      serializers/
      streaming/
```

И в общей картине:

```text
ingestion/ workers (existing)
chat/generation workers (new)
shared queue / observability backbone
```

---

# 6. Новый центральный объект: GenerationJob

## 6.1. Рекомендуемая модель

```python
class GenerationJob(BaseModel):
    id: str
    session_id: str
    message_id: str | None = None
    mode: str
    status: str
    idempotency_key: str
    visual_generation_plan: dict
    fashion_brief_hash: str | None = None
    prompt_hash: str | None = None
    style_id: str | None = None
    priority: str = "normal"
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failed_at: datetime | None = None
    failure_reason: str | None = None
    metadata: dict = {}
```

## 6.2. Почему нужен отдельный объект
Без `GenerationJob` невозможно:
- устойчиво трекать lifecycle генерации;
- реализовать retries;
- дедуплицировать повторные запросы;
- логировать и дебажить;
- отделить request layer от worker layer.

---

# 7. Status machine generation jobs

## 7.1. Рекомендуемые статусы

```python
class GenerationJobStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    READY = "ready"
    RUNNING = "running"
    PERSISTING = "persisting"
    COMPLETED = "completed"
    FAILED_RECOVERABLE = "failed_recoverable"
    FAILED_HARD = "failed_hard"
    CANCELLED = "cancelled"
```

## 7.2. Базовый flow

```text
API / orchestrator
→ create job
→ QUEUED
→ worker picks job
→ VALIDATING
→ RUNNING
→ PERSISTING
→ COMPLETED
```

При ошибках:

```text
RUNNING
→ FAILED_RECOVERABLE
→ retry
```

или:

```text
RUNNING
→ FAILED_HARD
```

## 7.3. Почему статусная модель обязательна
Это убирает “тишину” и превращает generation из opaque процесса в управляемый lifecycle.

---

# 8. GenerationRequest как граница между orchestrator и worker

Orchestrator не должен ставить в очередь “сырой prompt string”.  
Он должен ставить typed request:

```python
class GenerationRequest(BaseModel):
    session_id: str
    message_id: str | None = None
    mode: str
    visual_generation_plan: dict
    generation_metadata: dict
    idempotency_key: str
    priority: str = "normal"
```

## Почему это важно
Так worker получает:
- всё необходимое;
- без пересборки доменной логики;
- без повторного reasoning;
- без доступа к frontend/API контексту.

---

# 9. Role of orchestrator after Stage 10

После этого этапа orchestrator должен:
1. принять typed command;
2. resolve active mode;
3. получить knowledge bundle;
4. построить fashion brief;
5. построить visual generation plan;
6. если generation нужна — не вызывать Comfy напрямую;
7. вызвать `GenerationJobScheduler`;
8. вернуть `DecisionResult.text_and_generate(job_id=...)`.

То есть Stage 10 закрепляет, что orchestrator **никогда не выполняет тяжёлую генерацию сам**.

---

# 10. GenerationJobScheduler

## 10.1. Контракт

```python
class GenerationJobScheduler(Protocol):
    async def enqueue(self, request: GenerationRequest) -> str:
        ...
```

## 10.2. Ответственность
Scheduler должен:
- построить запись job;
- применить idempotency;
- выбрать очередь / priority;
- записать job в persistence;
- отправить execution task в queue backend;
- вернуть `job_id`.

## 10.3. Что он не делает
- не зовёт Comfy;
- не сохраняет image file;
- не формирует fashion brief;
- не занимается frontend delivery.

---

# 11. Worker architecture

## 11.1. Worker types

Stage 10 должен поддерживать хотя бы такие типы workers:

### 1. Image generation worker
Выполняет generation jobs:
- валидирует generation plan
- вызывает ComfyUI
- ждёт результат
- сохраняет media и metadata

### 2. Style ingestion worker
Уже существует концептуально через Этап 0:
- parser / scraper / normalizer / enricher jobs

### 3. Опционально позже
- generation cleanup worker
- reindex/search worker
- failed-job replay worker

## 11.2. Почему важно выделить worker types
Это позволяет:
- независимо масштабировать ingestion и generation;
- не смешивать heavy image jobs с parser jobs;
- приоритизировать user-facing jobs выше фоновых.

---

# 12. Queue backend strategy

## 12.1. Что допускает основной план
В основном плане прямо предложены:
- Redis + RQ
- Celery

То есть это осознанно backend-agnostic решение.

## 12.2. Практический подход
Для твоего проекта разумный поэтапный старт:

### Stage 10 initial
- Redis
- RQ или Celery
- один queue для generation
- отдельный queue/namespace для ingestion

### Stage 10+ scaling
- separate workers by queue
- priority queues
- retries / DLQ
- SSE/websocket status push

## 12.3. Архитектурное правило
Выбор Redis/RQ/Celery — это infrastructure detail.  
Domain/Application слой не должен от него зависеть.

---

# 13. Idempotency — обязательная часть архитектуры

Это один из самых важных пунктов этапа.

## 13.1. Почему
Без idempotency пользователь:
- нажмёт кнопку дважды;
- обновит страницу;
- повторно отправит follow-up;
- сеть сделает retry;
- frontend отправит duplicate request.

И ты получишь 2–3 одинаковых generation jobs.

## 13.2. Что нужно
У каждой generation job должен быть:
- `client_message_id`
- `idempotency_key`

### Пример логики ключа
Можно строить ключ из:
- `session_id`
- `message_id`
- `mode`
- `fashion_brief_hash`
- `visual_generation_plan_hash`

## 13.3. Правило
Если enqueue приходит с тем же idempotency key и job уже:
- queued
- running
- completed

система должна вернуть существующий `job_id`, а не создавать новый.

---

# 14. Persistence layer для jobs и результатов

## 14.1. Что хранить
Должны существовать:
- `generation_jobs`
- `generation_results`
- возможно `generation_job_events`

## 14.2. Что лежит в `generation_results`
- `job_id`
- media path / url
- image dimensions
- final prompt
- negative prompt
- style_id
- visual preset
- seed
- palette tags
- garments tags
- workflow metadata
- timestamps
- failure info if partial

## 14.3. Почему это важно
Это связывает Stage 9 (Comfy metadata) и Stage 10 (job lifecycle).

---

# 15. Failure handling and retry policy

## 15.1. Типы ошибок
Ошибки должны делиться минимум на:

### Recoverable
- временно недоступен ComfyUI
- network timeout
- Redis hiccup
- transient GPU overload
- media storage temporary issue

### Hard
- invalid generation plan
- missing workflow
- corrupted payload
- unsupported preset
- missing required fields

## 15.2. JobRetryPolicy
Нужен отдельный policy:

```python
class JobRetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_strategy: str = "exponential"
    retry_on: list[str] = []
```

## 15.3. Почему policy отдельно
Retry strategy не должна быть разбросана по worker-коду if-ами.

---

# 16. Связь Stage 10 со Stage 9 (Comfy pipeline)

Stage 9 уже ввёл:
- `VisualGenerationPlan`
- `VisualPreset`
- `GenerationMetadata`

Stage 10 закрепляет их как payload workers.

## Новый обязательный pipeline:

```text
Chat command
→ orchestrator
→ knowledge retrieval
→ fashion brief
→ image prompt compiler
→ visual generation plan
→ create generation job
→ worker executes plan in ComfyUI
→ result + metadata persisted
→ frontend fetches status/result
```

То есть Stage 10 — это execution backbone для всего visual generation слоя.

---

# 17. Связь Stage 10 со Stage 8 (knowledge layer)

Knowledge layer не должен жить только “до prompt builder”.

Важно, чтобы generation job сохранял:
- knowledge refs
- brief hash
- retrieved style references

Зачем:
- повторяемость;
- replay/debug;
- observability;
- анализ качества generation относительно retrieval.

---

# 18. Frontend contract after Stage 10

После ввода queue layer frontend должен работать так:

## 18.1. Immediate response
Backend отвечает быстро:

```json
{
  "decision_type": "text_and_generate",
  "reply_text": "Собрала для тебя образ в этом направлении.",
  "job_id": "gen_123",
  "flow_state": "generation_queued"
}
```

## 18.2. Далее frontend
- показывает текст;
- показывает pending image state;
- запускает polling / websocket / SSE;
- по `job_id` получает:
  - status
  - result
  - failure reason if needed

## 18.3. Почему это важно
Frontend больше не ждёт, пока Comfy закончит работу внутри одного HTTP-запроса.

---

# 19. Polling / SSE / WebSocket strategy

## 19.1. Что допускается
Основной план говорит: polling / websocket / SSE.
Это значит, что transport можно выбрать по зрелости проекта.

## 19.2. Рекомендуемый путь
Для поэтапного внедрения:

### First step
- polling by `job_id`

### Next step
- SSE for job status updates

### Later if needed
- WebSocket for richer multi-event UI

## 19.3. Архитектурное правило
Transport выбора статуса не должен менять доменную модель jobs.

---

# 20. Observability

## 20.1. Что логировать
Для каждой generation job:
- `job_id`
- `session_id`
- `message_id`
- `mode`
- `decision_type`
- `status_transition`
- `fashion_brief_hash`
- `visual_generation_plan_hash`
- `workflow_name`
- `visual_preset`
- `style_id`
- `provider`
- `retry_count`
- `failure_reason`

## 20.2. Метрики
- job enqueue success rate
- queue latency
- worker pickup latency
- generation duration
- success rate by mode
- retry rate
- duplicate prevented count
- failed hard / failed recoverable rate

---

# 21. Тестирование

## 21.1. Unit tests
Покрыть:
- `GenerationJobScheduler`
- `IdempotencyKeyBuilder`
- `GenerationStatusService`
- `JobRetryPolicy`
- status transitions

## 21.2. Integration tests
Покрыть:
- orchestrator -> enqueue job
- duplicate request returns same `job_id`
- worker completes job and persists result
- recoverable failure retries correctly
- parser jobs and generation jobs coexist in separate queues

## 21.3. E2E сценарии
Минимальный набор:
1. `garment_matching` → returns `job_id`, result comes later
2. `style_exploration` → duplicate click returns same `job_id`
3. `occasion_outfit` → status transitions visible in UI
4. Comfy temporary failure → recoverable retry
5. parser ingestion worker and generation worker run independently

---

# 22. Рекомендуемая модульная структура

```text
domain/generation_jobs/
  entities/
    generation_job.py
    generation_result.py
    generation_failure.py
  enums/
    generation_job_status.py
  value_objects/
    job_idempotency_key.py
    job_retry_policy.py

application/generation_jobs/
  services/
    generation_job_service.py
    generation_status_service.py
    generation_result_service.py
  use_cases/
    create_generation_job.py
    execute_generation_job.py
    complete_generation_job.py
    fail_generation_job.py

infrastructure/queue/
  adapters/
    rq_generation_scheduler.py
    celery_generation_scheduler.py
  workers/
    image_generation_worker.py
    style_ingestion_worker.py
  repositories/
    generation_job_repository.py
    generation_result_repository.py
```

---

# 23. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- оставлять generation как длинный sync HTTP flow;
- вызывать Comfy напрямую из API route;
- вызывать Comfy напрямую из orchestrator;
- не использовать idempotency;
- смешивать parser jobs и user-facing generation jobs без разделения очередей;
- не сохранять job lifecycle и metadata;
- пытаться “лечить таймауты” увеличением timeout вместо queue layer.

---

# 24. Пошаговый план реализации Этапа 10

## Подэтап 10.1. Ввести `GenerationJob`, `GenerationResult`, `GenerationJobStatus`
Создать центральные domain entities.

## Подэтап 10.2. Реализовать `GenerationJobScheduler`
Добавить enqueue abstraction и persistence.

## Подэтап 10.3. Реализовать `IdempotencyKeyBuilder`
Защититься от duplicate jobs.

## Подэтап 10.4. Реализовать image generation worker
Worker принимает structured `GenerationRequest` и исполняет `VisualGenerationPlan`.

## Подэтап 10.5. Связать с Stage 9
Worker получает не prompt string, а полный generation plan.

## Подэтап 10.6. Поднять status/result endpoints
Frontend должен видеть lifecycle job.

## Подэтап 10.7. Развести generation jobs и ingestion jobs по очередям
Использовать один execution backbone, но разные queues / worker pools.

## Подэтап 10.8. Добавить retries, observability и тесты
Сделать runtime устойчивым.

---

# 25. Критерии готовности этапа

Этап 10 реализован корректно, если:

1. Генерация больше не выполняется как длинный синхронный HTTP-сценарий.
2. Orchestrator создаёт generation job, а не вызывает Comfy напрямую.
3. Frontend получает `job_id` и работает по status/result contract.
4. В системе есть idempotency и duplicate protection.
5. Worker исполняет structured `VisualGenerationPlan`.
6. Parser/ingestion и generation используют единый job-driven подход, но разные очереди.
7. Job lifecycle и generation metadata сохраняются в persistence.
8. Runtime покрыт unit / integration / e2e тестами.
9. Система устойчива к временным сбоям Comfy и сети.
10. Queue layer готов к горизонтальному росту workers.

---

# 26. Архитектурный итог этапа

После реализации Этапа 10 проект получает полноценный **execution backbone**:

- orchestrator больше не блокируется тяжёлой генерацией;
- Comfy pipeline получает structured job execution model;
- frontend получает предсказуемый async UX;
- parser/ingestion и generation начинают жить в одной общей worker-driven архитектуре;
- система становится устойчивой, масштабируемой и пригодной для production-style эволюции.

Именно этот этап превращает все предыдущие архитектурные улучшения — orchestrator, knowledge layer, prompt pipeline, Comfy presets — в реальный устойчивый runtime, а не просто в хорошие внутренние abstractions.
