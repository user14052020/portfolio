# Server Setup Checklist

## Цель

Подготовить сервер так, чтобы проект был готов к:

- chat requests;
- LLM reasoning;
- image generation;
- позже video generation;
- каталогу вещей и парсингу источников.

## Базовая топология

Рекомендуемая схема сервисов на сервере:

- `nginx` или другой reverse proxy;
- `frontend`;
- `backend`;
- `postgres`;
- `redis`;
- `elasticsearch` при необходимости поиска по контенту;
- `ollama` как text model service;
- `comfyui` как media generation service;
- `worker` / `scheduler` для background jobs;
- storage для медиа и кэша.

## Сетевые правила

- Не публиковать `postgres`, `redis`, `elasticsearch` наружу.
- Не публиковать `ComfyUI` наружу без крайней необходимости.
- Доступ к `ComfyUI` разрешать только backend/worker.
- Снаружи оставить только:
  - `frontend`;
  - `backend API`;
  - admin endpoints только если есть auth и rate limit.

## Очереди и фоновые задачи

Нужно вынести в background jobs:

- отправку workflow в ComfyUI;
- polling статуса generation jobs;
- скачивание и обработку изображений из parser pipeline;
- построение embeddings и индексов;
- дедупликацию карточек товаров;
- очистку временных файлов.

## Что сделать первым делом

- [ ] Привести `docker-compose` или server orchestration к production-like виду.
- [ ] Добавить отдельный process для worker jobs.
- [ ] Убедиться, что `ComfyUI` доступен backend по внутреннему адресу.
- [ ] Проверить, что модели ComfyUI лежат на постоянном диске.
- [ ] Настроить healthchecks для backend, database, redis и comfy bridge.
- [ ] Добавить логирование ошибок генерации.
- [ ] Настроить автоматический перезапуск сервисов.

## Что сделать по LLM

- [ ] Поднять `Ollama` на сервере.
- [ ] Выбрать 1 стартовую текстовую модель для стилиста.
- [ ] Сделать внутренний endpoint `POST /stylist/reason`.
- [ ] Вынести системный prompt и tone policy в отдельный конфиг.
- [ ] Добавить fallback, если LLM временно недоступен.

## Что сделать по ComfyUI

- [ ] Зафиксировать 1 production workflow для outfit image generation.
- [ ] Зафиксировать 1 workflow для image-to-image / reference image.
- [ ] Проверить таймауты, queue latency и среднее время первой картинки.
- [ ] Вести versioning workflow JSON в git.
- [ ] Хранить список обязательных моделей и их путей.
- [ ] Добавить smoke-test workflow для диагностики после рестарта сервера.

## Что сделать по данным и хранилищу

- [ ] Решить, где храним итоговые картинки:
  - локально;
  - S3-compatible storage;
  - CDN later.
- [ ] Отделить temporary cache от permanent media.
- [ ] Настроить ротацию логов.
- [ ] Настроить очистку временных job artifacts.

## Наблюдаемость

- [ ] Логировать время ответа chat endpoint.
- [ ] Логировать время LLM reasoning.
- [ ] Логировать время enqueue в ComfyUI.
- [ ] Логировать полное время generation job до completed/failed.
- [ ] Отдельно считать:
  - успешные генерации;
  - failed jobs;
  - среднюю latency;
  - hit rate каталога.

## Безопасность

- [ ] Закрыть прямой внешний доступ к внутренним AI сервисам.
- [ ] Хранить секреты в `.env`, но для production перейти на secrets manager или systemd environment files.
- [ ] Ограничить размер upload.
- [ ] Добавить basic abuse protection:
  - rate limit;
  - file validation;
  - mime validation;
  - timeout budgets.

## Критерий готовности сервера

Сервер считаем готовым к следующему этапу, если:

- пользователь получает текстовый ответ без долгого блокирования UI;
- generation job создаётся и обновляется асинхронно;
- backend не падает при недоступности ComfyUI;
- LLM и ComfyUI можно перезапускать независимо;
- parser jobs не мешают чату.
