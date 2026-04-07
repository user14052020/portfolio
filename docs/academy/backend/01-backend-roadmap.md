# Backend Roadmap

Этот блок объясняет серверную часть от Python и FastAPI до базы, интеграций и фоновых задач.

## Учебные главы

### 01. Что такое Python backend

Разобрать:
- почему backend написан на Python;
- что такое модуль;
- пакет;
- импорт;
- async/await;
- чем такой backend отличается от Django-подхода.

Ключевые файлы:
- `apps/backend/requirements.txt`
- `apps/backend/app/main.py`

### 02. Что такое FastAPI

Разобрать:
- приложение;
- роут;
- dependency injection;
- schema validation;
- response model.

Файлы:
- `apps/backend/app/main.py`
- `apps/backend/app/api/router.py`
- `apps/backend/app/api/deps.py`
- `apps/backend/app/api/routes/*.py`

Отдельно пояснить:
- чем FastAPI отличается от Django и Django REST Framework;
- почему для этого проекта выбран более лёгкий API-oriented стек.

### 03. Архитектура backend в этом проекте

Разобрать:
- `api`
- `schemas`
- `services`
- `repositories`
- `models`
- `integrations`
- `tasks`
- `core`
- `db`
- `utils`

### 04. Что такое Pydantic schemas

Разобрать:
- request DTO;
- response DTO;
- валидация;
- сериализация.

Файлы:
- `apps/backend/app/schemas/*.py`

### 05. Что такое SQLAlchemy models

Разобрать:
- ORM;
- модель;
- таблица;
- relationship;
- enum;
- mixin.

Файлы:
- `apps/backend/app/models/*.py`

### 06. Что такое repository layer

Разобрать:
- зачем репозиторий выносят отдельно;
- CRUD;
- session;
- select/update/delete.

Файлы:
- `apps/backend/app/repositories/base.py`
- `apps/backend/app/repositories/*.py`

### 07. Что такое service layer

Разобрать:
- бизнес-логика;
- orchestration;
- чем service отличается от route и repository.

Файлы:
- `apps/backend/app/services/auth.py`
- `apps/backend/app/services/generation.py`
- `apps/backend/app/services/stylist_conversational.py`
- `apps/backend/app/services/stylist_prompt_policy.py`
- `apps/backend/app/services/search.py`
- `apps/backend/app/services/uploads.py`

### 08. Что такое интеграции

Разобрать:
- внешний сервис;
- API client;
- adapter;
- provider;
- retry;
- timeout.

Файлы:
- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/integrations/elasticsearch.py`
- `apps/backend/app/integrations/workflows/fashion_flatlay.json`

### 08a. REST API vs GraphQL на стороне backend

Разобрать:
- почему текущий проект использует REST;
- как выглядела бы эта система через GraphQL;
- где GraphQL мог бы помочь, а где усложнил бы систему без реальной пользы.

### 09. Что такое generation job

Разобрать:
- жизненный цикл job;
- queued/running/completed/failed/cancelled;
- operation log;
- polling;
- timeout;
- delete/cancel.

Файлы:
- `apps/backend/app/models/generation_job.py`
- `apps/backend/app/repositories/generation_jobs.py`
- `apps/backend/app/services/generation.py`
- `apps/backend/app/tasks/generation_polling.py`
- `apps/backend/app/api/routes/generation_jobs.py`

### 10. Что такое chat flow стилиста

Разобрать:
- история сообщений;
- prompt policy;
- structured output от LLM;
- upload flow;
- style exploration;
- generation trigger.

Файлы:
- `apps/backend/app/models/chat_message.py`
- `apps/backend/app/repositories/chat_messages.py`
- `apps/backend/app/schemas/stylist.py`
- `apps/backend/app/services/stylist_conversational.py`
- `apps/backend/app/services/stylist_prompt_policy.py`
- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/api/routes/stylist_chat.py`

### 11. Что такое Alembic migration

Разобрать:
- изменение схемы;
- revision;
- upgrade/downgrade;
- как читать миграции проекта.

Файлы:
- `apps/backend/alembic/env.py`
- `apps/backend/alembic/script.py.mako`
- `apps/backend/alembic/versions/*.py`

### 12. Продовые backend-паттерны и anti-patterns

Разобрать:
- почему прямой доступ к БД из роутов считается плохой практикой;
- почему route должен валидировать вход и вызывать service;
- зачем repository и service разделяются;
- что даёт async DB access;
- зачем нужны DI, versioned API и healthcheck;
- почему нужны сервисные исключения и глобальные обработчики;
- почему вычисления в памяти становятся red flag под нагрузкой.

Файлы:
- `apps/backend/app/api/routes/*.py`
- `apps/backend/app/api/deps.py`
- `apps/backend/app/db/session.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/*.py`
- `apps/backend/app/repositories/*.py`

## Инвентаризация backend-файлов по разделам

### Конфиги и вход

- `apps/backend/requirements.txt`
- `apps/backend/Dockerfile`
- `apps/backend/alembic.ini`
- `apps/backend/app/main.py`
- `apps/backend/app/core/config.py`
- `apps/backend/app/core/security.py`

### API

- `apps/backend/app/api/deps.py`
- `apps/backend/app/api/router.py`
- `apps/backend/app/api/routes/*.py`

### DB

- `apps/backend/app/db/base.py`
- `apps/backend/app/db/session.py`

### Models

- `apps/backend/app/models/*.py`

### Schemas

- `apps/backend/app/schemas/*.py`

### Repositories

- `apps/backend/app/repositories/*.py`

### Services

- `apps/backend/app/services/*.py`

### Integrations

- `apps/backend/app/integrations/*.py`
- `apps/backend/app/integrations/workflows/fashion_flatlay.json`

### Tasks

- `apps/backend/app/tasks/generation_polling.py`

### Migrations and scripts

- `apps/backend/alembic/*`
- `apps/backend/scripts/seed.py`

## Что потом разбирать до строк и функций в первую очередь

- `apps/backend/app/main.py`
- `apps/backend/app/api/router.py`
- `apps/backend/app/api/routes/stylist_chat.py`
- `apps/backend/app/services/stylist_conversational.py`
- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/services/generation.py`
- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/db/session.py`
- `apps/backend/app/models/generation_job.py`
- `apps/backend/alembic/versions/202603300001_initial.py`

## Связанный план

- [02-backend-file-atlas-plan.md](./02-backend-file-atlas-plan.md) — подробная карта backend-файлов для послойного разбора.
- [03-backend-production-patterns-plan.md](./03-backend-production-patterns-plan.md) — обязательный план разбора продовых backend-паттернов и улучшений.
