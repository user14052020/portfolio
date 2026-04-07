# Runtime And Ops Atlas Plan

Этот файл — план подробного разбора operational-слоя проекта.

## 1. Корневые operational-файлы

Нужно разобрать:
- `docker-compose.yml`
- `.env.example`
- `README.md`

## 2. Backend runtime files

Нужно разобрать:
- `apps/backend/Dockerfile`
- `apps/backend/alembic.ini`
- `apps/backend/requirements.txt`
- `apps/backend/scripts/seed.py`

## 3. Frontend runtime files

Нужно разобрать:
- `apps/frontend/Dockerfile`
- `apps/frontend/package.json`

## 4. Runtime reference docs

Нужно разобрать:
- `docs/06-autostart-map.md`
- `docs/07-vllm-runtime-reference.md`
- `docs/08-comfyui-runtime-reference.md`
- `docs/09-ai-runtime-docs-index.md`
- `docs/10-models-in-use.md`

## 5. Сценарии эксплуатации, которые нужно описать

Позже в atlas должны появиться пошаговые разборы:
- как поднять проект после клона репозитория;
- как применить миграции;
- как проверить backend health;
- как проверить frontend;
- как проверить связку backend -> vLLM;
- как проверить связку backend -> ComfyUI;
- как читать логи;
- как диагностировать зависшую generation job;
- как перезапускать сервисы безопасно.

## 6. Формат разбора operational-файла

Для каждого файла позже нужно отвечать:
1. Кто его читает: человек, Docker, shell, сервис или runtime.
2. Когда он используется: build time, startup time, runtime или debugging time.
3. Какие параметры в нём критичны.
4. Что произойдёт, если параметр неверен.
5. Какие команды нужно знать рядом с этим файлом.
