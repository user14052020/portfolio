# Backend File Atlas Plan

Этот файл — план полного разбора backend-файлов.

## 1. Точка входа и базовые конфиги

Нужно разобрать:
- `apps/backend/requirements.txt`
- `apps/backend/Dockerfile`
- `apps/backend/alembic.ini`
- `apps/backend/app/main.py`
- `apps/backend/app/core/config.py`
- `apps/backend/app/core/security.py`

## 2. API layer

Нужно разобрать:
- `apps/backend/app/api/router.py`
- `apps/backend/app/api/deps.py`
- `apps/backend/app/api/routes/auth.py`
- `apps/backend/app/api/routes/blog_posts.py`
- `apps/backend/app/api/routes/contact_requests.py`
- `apps/backend/app/api/routes/generation_jobs.py`
- `apps/backend/app/api/routes/projects.py`
- `apps/backend/app/api/routes/site_settings.py`
- `apps/backend/app/api/routes/stylist_chat.py`
- `apps/backend/app/api/routes/uploads.py`
- `apps/backend/app/api/routes/users.py`

## 3. DB layer

Нужно разобрать:
- `apps/backend/app/db/base.py`
- `apps/backend/app/db/session.py`

## 4. Models

Нужно разобрать все модели из:
- `apps/backend/app/models/*.py`

Особый приоритет:
- `generation_job.py`
- `chat_message.py`
- `uploaded_asset.py`
- `user.py`
- `project.py`
- `blog.py`

## 5. Schemas

Нужно разобрать все схемы из:
- `apps/backend/app/schemas/*.py`

Особый приоритет:
- `stylist.py`
- `generation_job.py`
- `upload.py`
- `project.py`
- `site_settings.py`

## 6. Repositories

Нужно разобрать:
- `apps/backend/app/repositories/base.py`
- `apps/backend/app/repositories/chat_messages.py`
- `apps/backend/app/repositories/generation_jobs.py`
- `apps/backend/app/repositories/projects.py`
- остальные repository-файлы

## 7. Services

Нужно разобрать:
- `apps/backend/app/services/stylist_conversational.py`
- `apps/backend/app/services/stylist_prompt_policy.py`
- `apps/backend/app/services/generation.py`
- `apps/backend/app/services/search.py`
- `apps/backend/app/services/uploads.py`
- `apps/backend/app/services/auth.py`

## 8. Integrations

Нужно разобрать:
- `apps/backend/app/integrations/vllm.py`
- `apps/backend/app/integrations/comfyui.py`
- `apps/backend/app/integrations/elasticsearch.py`
- `apps/backend/app/integrations/workflows/fashion_flatlay.json`

## 9. Tasks and background flows

Нужно разобрать:
- `apps/backend/app/tasks/generation_polling.py`

## 10. Migrations and seed tooling

Нужно разобрать:
- `apps/backend/alembic/env.py`
- `apps/backend/alembic/script.py.mako`
- `apps/backend/alembic/versions/*.py`
- `apps/backend/scripts/seed.py`

## Формат разбора одного backend-файла

Для каждого файла позже нужно отвечать:
1. Это конфиг, route, schema, model, repository, service, integration или task.
2. Какие сущности он экспортирует.
3. Какие зависимости он получает на вход.
4. Какие сайд-эффекты создаёт.
5. Какие таблицы, API, очереди или внешние сервисы он трогает.
6. Какие строки в нём ключевые.
