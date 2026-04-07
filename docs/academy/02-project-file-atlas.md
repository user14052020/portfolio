# Project File Atlas Plan

Этот файл задаёт общий план полного разбора файлов проекта `portfolio`.

## Зачем нужен file atlas

В обычной документации часто объясняют технологию, но не показывают, где она живёт в кодовой базе.  
Здесь будет обратный подход:
- сначала выделяем слои проекта;
- затем для каждого слоя составляем перечень важных файлов;
- потом разбираем эти файлы по одному: зачем они нужны, что в них главное и как они связаны с соседями.

## Слои разбора

### Корень репозитория

Будут разобраны:
- `.env.example`
- `.gitignore`
- `.gitattributes`
- `docker-compose.yml`
- `README.md`

### Frontend

Будут разобраны:
- конфиги Node/Next/Tailwind/TypeScript;
- entry files App Router;
- feature layer;
- entity layer;
- shared layer;
- chat UI;
- admin UI.

### Backend

Будут разобраны:
- entrypoint;
- core config;
- db layer;
- models;
- schemas;
- repositories;
- services;
- integrations;
- background tasks;
- migrations.

### Infrastructure

Будут разобраны:
- docker compose;
- env configuration;
- runtime docs;
- сетевые и operational-сценарии;
- vLLM и ComfyUI runtime maps.

## Формат разбора одного файла

Для каждого файла в atlas будет отдельный мини-раздел:
1. Где лежит файл.
2. К какому слою он относится.
3. Зачем он нужен.
4. Кто его вызывает или импортирует.
5. Какие ключевые сущности в нём находятся.
6. Что будет, если файл изменить.
7. Какие файлы нужно читать сразу после него.

## Порядок разбора

1. Сначала корневые конфиги.
2. Потом инфраструктурные точки входа.
3. Затем frontend entrypoints и API layer.
4. Затем backend entrypoints, роуты и сервисы.
5. После этого — модели, миграции, интеграции и фоновые задачи.

## Где детализируются карты файлов

- [frontend/02-frontend-file-atlas-plan.md](./frontend/02-frontend-file-atlas-plan.md)
- [backend/02-backend-file-atlas-plan.md](./backend/02-backend-file-atlas-plan.md)
- [infrastructure/02-runtime-and-ops-atlas-plan.md](./infrastructure/02-runtime-and-ops-atlas-plan.md)
