# Style GPT enrichment runbook

Этот документ описывает, как запускать новый `style enrichment` слой: брать уже сохраненные данные по стилям из БД, отправлять их в ChatGPT/OpenAI и обновлять enriched facet tables.

Важно: это не старый parser ingestion. Запускается отдельный скрипт:

```sh
./scripts/run_style_enrichment_entrypoint.sh
```

Он вызывает:

```sh
python3 scripts/run_style_enrichment.py
```

## 1. Что делает запуск

Один enrichment run:

1. Берет `style_id`.
2. Загружает сохраненный source material из БД.
3. Собирает cleaned source text и evidence.
4. Отправляет payload в ChatGPT/OpenAI.
5. Получает structured JSON.
6. Валидирует payload.
7. Пишет новые данные в enrichment/facet таблицы.
8. Пишет лог enrichment run.

Основные таблицы результата:

- `style_llm_enrichments`
- `style_knowledge_facets`
- `style_visual_facets`
- `style_fashion_item_facets`
- `style_image_facets`
- `style_relation_facets`
- `style_presentation_facets`

## 2. Нужные env-переменные

Перед запуском в `.env` должны быть заданы:

```env
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=45
```

`OPENAI_API_KEY` обязателен. Без него скрипт завершится ошибкой конфигурации.

Если `.env` менялся после старта контейнеров, перезапусти backend-контейнер без сборки:

```sh
sudo docker compose up -d --force-recreate backend
```

## 3. Базовый формат команды

Все команды запускаются из корня проекта на сервере, где работает Docker Compose:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh <ARGS>"
```

Если Docker не требует `sudo`, можно убрать `sudo`.

## 4. Проверить один стиль без записи

Dry-run не пишет facet rows и logs в БД, но все равно отправляет запрос в GPT и тратит токены.

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode single --style-id 123 --dry-run"
```

Смотри в выводе:

- `style_enrichment_command_started`
- `style_enrichment_run_started`
- `style_enrichment_run_finished`
- `style_enrichment_command_finished`
- `succeeded_count`
- `failed_count`
- `items[].status`

## 5. Обновить один стиль с записью в БД

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode single --style-id 123"
```

Если стиль уже enriched текущей facet version и нужно именно пересобрать данные заново:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode single --style-id 123 --overwrite-existing"
```

## 6. Запустить несколько конкретных стилей

Используй `batch` + `--style-ids`:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode batch --style-ids 123,124,125 --dry-run"
```

После проверки убрать `--dry-run`:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode batch --style-ids 123,124,125"
```

Для принудительной пересборки уже enriched стилей:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode batch --style-ids 123,124,125 --overwrite-existing"
```

## 7. Идти по стилям один за другим через offset/limit

Для одного стиля за раз используй `--limit 1`.

Первый стиль:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 1 --offset 0"
```

Следующий стиль:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 1 --offset 1"
```

Дальше увеличивать `offset` на `1`:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 1 --offset 2"
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 1 --offset 3"
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 1 --offset 4"
```

Важно: `offset` считается по списку `styles`, отсортированному по `id ASC`, исключая `archived`. Это не offset по "еще не enriched" стилям.

## 8. Идти пачками через offset/limit

Безопасный старт: пачки по `5` или `10`.

Первая пачка:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset 0"
```

Вторая пачка:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset 10"
```

Третья пачка:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset 20"
```

Правило:

```text
next_offset = previous_offset + limit
```

Если нужно обновлять уже enriched стили, добавь `--overwrite-existing`:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset 0 --overwrite-existing"
```

## 9. Автоматический проход пачками

Пример прохода по первым 100 стилям пачками по 10:

```sh
for offset in 0 10 20 30 40 50 60 70 80 90; do
  sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset ${offset}"
done
```

Для принудительной пересборки:

```sh
for offset in 0 10 20 30 40 50 60 70 80 90; do
  sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode full-backfill --limit 10 --offset ${offset} --overwrite-existing"
done
```

## 10. Повторить только упавшие стили

Сначала маленькая проверка:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode retry-failed --limit 5 --dry-run"
```

Потом реальный retry:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode retry-failed --limit 5"
```

Если нужно перезаписать существующие facets при retry:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode retry-failed --limit 5 --overwrite-existing"
```

## 11. Как читать результат

В конце команда печатает JSON. Главные поля:

- `selected_count`: сколько styles выбрано по `limit/offset/style_ids`;
- `processed_count`: сколько реально отправлено в enrichment;
- `succeeded_count`: сколько успешно обработано;
- `failed_count`: сколько упало;
- `skipped_existing_count`: сколько пропущено, потому что current facet version уже есть;
- `items[].style_id`: style id;
- `items[].style_slug`: slug;
- `items[].status`: статус по стилю;
- `items[].did_write`: были ли записи в БД.

Если `skipped_existing_count` высокий, а нужно именно обновить данные, запускай с `--overwrite-existing`.

## 12. Рекомендуемый безопасный порядок

1. Проверить env.
2. Перезапустить backend-контейнер, если env менялся.
3. Запустить один стиль с `--dry-run`.
4. Запустить тот же стиль без `--dry-run`.
5. Запустить пачку `--limit 5 --offset 0`.
6. Если все хорошо, увеличить до `--limit 10` или `--limit 20`.
7. Двигаться по offset: `0`, `10`, `20`, `30` и так далее.
8. Для пересборки уже enriched данных добавлять `--overwrite-existing`.

## 13. Частые ошибки

`OPENAI_API_KEY is not configured for style enrichment`

Значит в `.env` нет `OPENAI_API_KEY`, или backend-контейнер не был пересоздан после изменения `.env`.

`failed_source_load`

У style нет сохраненного source row/source text. Сначала нужно прогнать обычный parser ingestion для этого стиля.

`skipped_existing`

Стиль уже enriched текущей facet version. Для пересборки добавь `--overwrite-existing`.

`failed_count > 0`

Посмотри `items[].error_message`, затем используй:

```sh
sudo docker compose exec backend sh -lc "cd /app && ./scripts/run_style_enrichment_entrypoint.sh --mode retry-failed --limit 10"
```
