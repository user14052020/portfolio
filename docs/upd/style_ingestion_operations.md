# Операционный Runbook По Style Ingestion

Обновлено: 2026-04-09

## Статус

Этап 0 по `style_ingestion_plan.md` закрыт на уровне кода и считается готовым к `rsync` и запуску в Docker.

Локально на Windows parser запускать не нужно.

Рабочая среда для запуска:

- Ubuntu VM
- `docker compose`
- backend-контейнер проекта

## Что Уже Должно Быть На VM

- актуальное дерево проекта после `rsync`
- поднятый `docker compose`
- доступный сервис `backend`
- примененные миграции базы

## Базовый Entry Point Внутри Контейнера

В backend-контейнере добавлен стабильный entrypoint:

- [run_style_ingestion_entrypoint.sh](/c:/dev/portfolio/apps/backend/scripts/run_style_ingestion_entrypoint.sh)

Он запускает:

```sh
python3 scripts/run_style_ingestion.py
```

из каталога `/app`.

## Подготовка После Rsync

Сначала применяем миграции:

```bash
docker compose exec backend sh -lc "cd /app && alembic -c alembic.ini upgrade head"
```

Если backend-контейнер уже запущен в dev-режиме с bind mount, отдельный rebuild обычно не нужен.

## Безопасная Рабочая Последовательность

### 1. Проверить discovery без записи в БД

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode discover --dry-run --limit 10"
```

### 2. Проверить matching без записи

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode match --dry-run --limit 10"
```

### 3. Зафиксировать matching

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode match --limit 10"
```

### 4. Посмотреть очередь ручной модерации ambiguous matches

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-list --review-limit 20"
```

### 5. Подтвердить ambiguous match вручную

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-resolve --match-id 123 --resolution confirm_candidate --style-direction-id 456 --review-note 'Подтверждено вручную'"
```

### 6. Отклонить ambiguous match вручную

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-resolve --match-id 123 --resolution reject_candidate --review-note 'Спорное совпадение отклонено'"
```

### 7. Проверить controlled merge без записи

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode merge --dry-run --merge-limit 20"
```

### 8. Зафиксировать controlled merge

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode merge --merge-limit 20"
```

### 9. Проверить batch ingestion без записи

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --dry-run --limit 5"
```

### 10. Запустить малый batch ingestion

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --limit 5"
```

### 11. Продолжить прерванный batch ingestion

Если batch-run был прерван, можно продолжить его по `style_ingest_runs.id`:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --resume-run-id 123"
```

Resume допускается только для `aborted`, `failed` и `completed_with_failures`, если в batch ещё остались необработанные кандидаты.

### 12. Показать последние ingest runs и найти resumable batch

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-list --run-limit 20"
```

`run-list` теперь показывает не только статус, но и `progress_percent`, `remaining_count`, `resume_available`, `abort_available`, `active_error_type`, `completed_normally`, `terminal_state_family`, последний обработанный стиль, URL, последнюю candidate-ошибку и `fatal_error` для аварийно оборвавшегося batch-run.

### 13. Аварийно остановить зависший batch-run

Если run завис в статусе `running` и нужно освободить source для нового запуска или resume:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-abort --run-id 123"
```

Статусы run:

- `running` — ingestion ещё идёт
- `completed` — run завершён без ошибок
- `completed_with_failures` — run завершён, но часть кандидатов упала
- `failed` — run аварийно оборвался
- `aborted` — run остановлен оператором и может быть продолжен через `resume-run-id`

## Рекомендуемый Режим Эксплуатации

Начинать только маленькими пачками:

- `discover` / `match` по `10`
- `merge` по `20`
- `batch` по `5`

И только после нескольких успешных прогонов постепенно увеличивать лимиты.

## Что Делать Нельзя

- не запускать сразу большой `batch` на сотни страниц
- не запускать два `batch`-run одновременно для одного и того же source
- не пропускать этап `match -> review -> merge`
- не запускать `review-resolve` в расчете на dry-run: этот режим намеренно только записывающий
- не запускать parser локально на Windows-хосте вместо Docker

## Почему Схема Считается Production-Friendly

- source ingestion отделен от chat runtime
- matching отделен от merge
- ambiguous кейсы не теряются и идут в persistent review queue
- manual решения не перетираются auto-path логикой
- legacy `style_directions` и canonical `styles` связаны через отдельный link-layer
- везде есть dry-run для безопасной проверки перед записью
- batch crawler работает последовательно и с безопасными лимитами
- discovery опирается только на trusted-source index и не использует bootstrap из `styles-1.txt` / `styles-2.txt`

## Минимальный Операционный Цикл

Для первого запуска после `rsync`:

1. `alembic upgrade head`
2. `discover --dry-run`
3. `match --dry-run`
4. `match`
5. `review-list`
6. `review-resolve` для ambiguous
7. `merge --dry-run`
8. `merge`
9. `batch --dry-run`
10. `batch`
