# Infrastructure Roadmap

Этот блок объясняет, где проект физически живёт и какие сервисы обеспечивают его работу.

## Главы

### 01. Docker и контейнеры

Разобрать:
- что такое контейнер;
- образ;
- слой;
- volume;
- сеть контейнеров;
- чем контейнер отличается от виртуальной машины.

Файлы проекта:
- `docker-compose.yml`
- `apps/frontend/Dockerfile`
- `apps/backend/Dockerfile`

### 01a. Git и CI/CD как часть инженерного контура

Разобрать:
- что такое Git;
- что такое commit, branch, remote;
- что такое CI/CD pipeline;
- как код проходит путь от локальной машины до сервера.

### 02. Переменные окружения

Разобрать:
- что такое `.env`;
- зачем нужен `.env.example`;
- как backend и frontend получают конфиг;
- где опасно хранить секреты.

Файлы проекта:
- `.env.example`
- `apps/frontend/src/shared/config/env.ts`
- `apps/backend/app/core/config.py`

### 03. PostgreSQL

Разобрать:
- зачем проекту основная реляционная база;
- какие сущности там лежат;
- как backend подключается к Postgres;
- чем Postgres отличается от MongoDB.

Файлы проекта:
- `apps/backend/app/db/session.py`
- `apps/backend/app/models/*`
- `apps/backend/alembic/*`

### 04. Redis

Разобрать:
- зачем нужен быстрый in-memory storage;
- кэш;
- временные данные;
- почему Redis не заменяет Postgres.

Файлы проекта:
- `docker-compose.yml`
- `apps/backend/app/services/generation.py`

### 05. Elasticsearch

Разобрать:
- зачем нужен поиск;
- индекс;
- документ;
- полнотекстовый поиск;
- отличие от SQL search.

Файлы проекта:
- `apps/backend/app/integrations/elasticsearch.py`
- `apps/backend/app/services/search.py`

### 06. Alembic и миграции

Разобрать:
- что такое migration;
- зачем она нужна;
- чем migration отличается от seed;
- как схема БД меняется во времени.

Файлы проекта:
- `apps/backend/alembic.ini`
- `apps/backend/alembic/env.py`
- `apps/backend/alembic/versions/*.py`
- `apps/backend/scripts/seed.py`

### 07. vLLM

Разобрать:
- что такое inference server;
- что такое модель;
- что такое structured output;
- почему backend не вызывает LLM напрямую из браузера.

Файлы проекта:
- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/services/stylist_prompt_policy.py`
- `apps/backend/app/services/stylist_conversational.py`
- `docs/07-vllm-runtime-reference.md`

### 08. ComfyUI

Разобрать:
- что такое node-based image generation runtime;
- workflow;
- prompt;
- queue;
- polling;
- image result.

Файлы проекта:
- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/integrations/workflows/fashion_flatlay.json`
- `apps/backend/app/services/generation.py`
- `apps/backend/app/tasks/generation_polling.py`
- `docs/08-comfyui-runtime-reference.md`
- `docs/10-models-in-use.md`

### 09. Host, VM, WSL и сеть

Разобрать:
- Windows host;
- Ubuntu VM;
- WSL;
- зачем сервисы разделены;
- как они видят друг друга по IP и портам.

Связанные docs:
- `docs/01-host-vm-network-check.md`
- `docs/02-vllm-on-win11-host.md`
- `docs/03-vm-env-and-smoke-tests.md`
- `docs/06-autostart-map.md`

### 10. Nginx, cloud infrastructure и CDN

Разобрать:
- что такое reverse proxy;
- зачем обычно ставят Nginx перед приложением;
- как проект можно было бы разворачивать в AWS / GCP / DigitalOcean;
- что такое CDN и как он влияет на статику и media.

### 11. Polling vs WebSockets на инфраструктурном уровне

Разобрать:
- когда хватает HTTP polling;
- когда нужен постоянный real-time канал;
- как выбор между polling и WebSockets влияет на backend, frontend и operations.

## Практические темы для следующих итераций

- как читать `docker compose logs`;
- как понять, где упал сервис;
- как проверить доступность порта;
- как миграция меняет реальную таблицу;
- как generation job проходит путь от API до результата.

## Связанный план

- [02-runtime-and-ops-atlas-plan.md](./02-runtime-and-ops-atlas-plan.md) — карта runtime и operational-файлов, которые будут разбираться отдельно.
