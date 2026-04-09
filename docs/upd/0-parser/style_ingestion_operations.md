# Операционный Runbook По Style Ingestion

Обновлено: 2026-04-09

## 1. Что Это Вообще Такое

`style ingestion` в этом проекте — это не часть чат-бота и не “один скрипт на парсинг”.
Это отдельный ingestion-контур, который:

1. находит страницы стилей у trusted source;
2. забирает сырые данные;
3. нормализует их в канонический каталог `styles`;
4. при необходимости связывает этот каталог с legacy-таблицей сайта `style_directions`.

Для `aesthetics_wiki` сейчас схема такая:

- discovery идёт через `MediaWiki Action API` по A-Z и taxonomy discovery pages;
- detail fetch идёт через `MediaWiki Action API`;
- HTML fetch/fallback contour из runtime parser-а убран;
- runtime fetch policy использует `source_fetch_state` и умеет `cooldown / blocked_suspected / next_allowed_at`;
- raw fetch metadata пишется отдельно;
- revision/page fingerprint сохраняется отдельно;
- discovery/taxonomy pages сохраняются как first-class `style_source_pages` и `style_source_page_versions`;
- detail snapshots сохраняют `raw_wikitext`, `parsed_html`, `raw_text`, `raw_sections`, `raw_links`;
- foundation для job-очереди уже создан и основной operational API-first путь теперь идёт через `enqueue-jobs` и `run-worker`.
- `run-worker` и ручной `process-next-job` берут source-level DB lease с heartbeat/TTL через `style_source_fetch_states`, поэтому у одного source одновременно работает только один worker.

Этот документ нужен для двух вещей:

- быстро понять, как устроен parser в проекте;
- безопасно запускать его в ручном или полуавтоматическом режиме.

Самая важная мысль:

- основной production-путь наполнения parser-каталога теперь `enqueue-jobs -> run-worker`;
- `batch` остаётся как legacy/manual fallback;
- `match / review / merge` не парсят сайт-донор, а связывают уже загруженный parser-каталог с legacy-структурой сайта;
- если нужна только knowledge base parser-а, основной путь теперь `enqueue-jobs + run-worker`;
- если нужно подключить эти данные к сайту, полный путь теперь `enqueue-jobs -> run-worker -> match -> review -> merge`.
- старые bootstrap-файлы `styles-1.txt` и `styles-2.txt` больше не используются и не должны участвовать в наполнении базы.

## 1.1. Быстрая Карта Режимов

Если задача такая:

- проверить одну страницу: `single`
- посмотреть, что parser вообще видит у источника: `discover`
- реально грузить стили в канонический каталог по основному API-first пути: `enqueue-jobs` + `run-worker`
- legacy/manual загрузка пачкой: `batch`
- поставить API discovery-job в очередь: `enqueue-jobs`
- обработать одну следующую job из очереди: `process-next-job`
- запустить постоянный API worker поверх очереди: `run-worker`
- сопоставить канонический каталог с `style_directions`: `match`
- разобрать спорные совпадения: `review-list` и `review-resolve`
- подтвердить безопасные связи legacy и canonical: `merge`
- смотреть прогресс и состояние прогонов: `run-list`
- аварийно остановить зависший `batch`: `run-abort`

## 2. Какой Путь Данных У Парсера

Структурно parser работает так:

1. `discover`
Находит кандидатов-стили у источника.

2. `detail fetch`
Забирает конкретную страницу стиля и её сырые данные.

Важно:
в job-driven API-пути detail-слой теперь сохраняет не только `raw_html/raw_wikitext`, но и структурный raw snapshot страницы: `raw_text`, `raw_sections`, `raw_links`.

3. `normalize/enrich`
Превращает сырой источник в нормализованный `style profile`, `traits`, `taxonomy`, `relations`.

4. `persist`
Пишет канонические данные в таблицы parser-слоя.

5. `match`
Сопоставляет найденные trusted-source стили с legacy-таблицей сайта `style_directions`.

6. `review / resolve`
Даёт оператору вручную разобрать спорные совпадения.

7. `merge`
Создаёт контролируемую связь между legacy `style_directions` и каноническими `styles`.

## 3. Какие Сущности Важно Понимать

### Канонический каталог

Это parser-слой, который строится из trusted source.

Основные таблицы:

- `style_sources`
- `style_source_sections`
- `style_source_links`
- `style_source_evidences`
- `styles`
- `style_profiles`
- `style_traits`
- `style_taxonomy_nodes`
- `style_taxonomy_links`
- `style_relations`

### Legacy-каталог сайта

Это существующая бизнес-таблица сайта:

- `style_directions`

Важно:
`style_directions` больше не должен наполняться из legacy `txt`-файлов.
Если каталог стилей нужно расширять или обновлять, это делается через API/job-driven parser-контур.

Она не равна каноническому parser-каталогу один в один. Поэтому нужны отдельные этапы:

- `match`
- `review`
- `merge`

### Операционный слой

Он нужен для контроля и диагностики работы parser-а.

Основные таблицы:

- `style_ingest_runs`
- `style_ingest_changes`
- `style_source_fetch_states`
- `style_source_fetch_logs`

Foundation под будущий worker/job-режим:

- `style_ingest_jobs`
- `style_source_pages`
- `style_source_page_versions`
- `style_ingest_attempts`

Важно:
сейчас эти foundation-таблицы уже не просто созданы: в `run_style_ingestion.py` уже есть минимальный job-driven контур.
В API-first режиме в них теперь реально сохраняются:

- style pages;
- discovery index page;
- taxonomy discovery pages (`family / type / color / decade / origin`);
- revision-aware raw snapshots с `raw_sections/raw_links`.

## 4. Где И Как Запускается Parser

Parser запускать нужно не на Windows-хосте, а внутри Ubuntu VM в `backend`-контейнере.

Корень проекта на VM:

```bash
~/projects/portfolio
```

Основной entrypoint:

- [run_style_ingestion_entrypoint.sh](/c:/dev/portfolio/apps/backend/scripts/run_style_ingestion_entrypoint.sh)

Он запускает:

```sh
python3 scripts/run_style_ingestion.py
```

Базовая форма любой команды:

```bash
cd ~/projects/portfolio
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh ..."
```

Перед первым запуском после `rsync`:

```bash
cd ~/projects/portfolio
docker compose exec backend sh -lc "cd /app && alembic -c alembic.ini upgrade head"
```

## 5. Что Делает Каждый Режим

### `single`

Назначение:
обработать одну конкретную страницу стиля.

Когда использовать:

- smoke-test новой страницы;
- диагностика parser-а;
- ручная догрузка одного style page.

Что делает:

- fetch одной страницы;
- normalize/enrich;
- запись в канонический parser-слой.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode single --style-title 'Dark Academia' --style-url 'https://aesthetics.fandom.com/wiki/Dark_Academia'"
```

### `discover`

Назначение:
показать, каких кандидатов parser вообще видит у источника.

Когда использовать:

- проверить, что trusted-source index сейчас читается корректно;
- понять, какие стили попадут в batch;
- отладить `offset`, `limit`, `title-contains`.

Что делает:

- только discovery;
- в `--dry-run` ничего не пишет в БД.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode discover --dry-run --limit 10"
```

### `batch`

Назначение:
обработать пачку discovered style pages и записать их в канонический parser-слой.

Когда использовать:

- наполнять `styles`, `style_profiles`, `style_traits`, `style_relations`;
- постепенно прогонять trusted source.

Что делает:

- берёт срез кандидатов через `offset + limit`;
- fetch/normalize/persist для каждой страницы;
- пишет `style_ingest_runs`.

Важно:
один `batch`-run не означает “обойти всё до конца”.
Один запуск `--mode batch` обрабатывает только один выбранный срез списка кандидатов.

Dry-run:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --dry-run --limit 5"
```

Реальный запуск:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --limit 5"
```

### `enqueue-jobs`

Назначение:
поставить в очередь отдельную discovery job для API-first pipeline.

Когда использовать:

- если хотите идти уже по `ingest_jobs`, а не по старому `batch-loop`;
- если нужен API-first переход от discovery к worker-контуру.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode enqueue-jobs --limit 10"
```

Что делает в текущей реализации:

- не бежит discovery inline в CLI-команде;
- создаёт first-class job `discover_source_pages` в `style_ingest_jobs`;
- дальше уже worker забирает её и сам делает API discovery, сохраняет discovery/taxonomy pages и ставит detail jobs.

Что делает дополнительно discovery job:

- сохраняет discovery index page в `style_source_pages` и `style_source_page_versions`;
- сохраняет taxonomy discovery pages туда же;
- использует `revision_id` для dedupe и не ставит новый detail fetch на уже сохранённую revision;
- taxonomy enrichment теперь берёт labels не только из section heading, но и из DOM-context taxonomy page;
- после этого ставит в очередь только нужные `fetch_style_page` jobs.

### `process-next-job`

Назначение:
выполнить одну следующую job из `style_ingest_jobs`.

Что делает:

- либо fetch одной style page через API;
- либо normalize/persist уже скачанной версии страницы.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode process-next-job"
```

### `run-worker`

Назначение:
крутить API job queue штатным worker-циклом, а не внешним bash-loop.

Что делает:

- повторяет `process-next-job`;
- если очередь пуста, спит `--worker-idle-seconds`;
- retryable fetch-ошибки не финализирует сразу, а возвращает в `queued` с backoff и новым `available_at`;
- перед claim возвращает в очередь stale `running` jobs после рестарта worker/container;
- может остановиться по `--worker-max-jobs` или `--worker-stop-when-idle`.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-worker --worker-max-jobs 21 --worker-stop-when-idle"
```

### `match`

Назначение:
сопоставить trusted-source стили с legacy `style_directions`.

Когда использовать:

- когда canonical parser-слой уже нужен сайту;
- когда надо связать новый каталог и старую таблицу направлений.

Что делает:

- сравнивает кандидатов источника с `style_directions`;
- делит результаты на:
  - `auto_matched`
  - `ambiguous`
  - `unmatched`

Dry-run:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode match --dry-run --limit 10"
```

Реальный запуск:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode match --limit 10"
```

### `review-list`

Назначение:
показать ambiguous matches, которые нельзя безопасно решить автоматически.

Когда использовать:

- после `match`;
- перед `merge`.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-list --review-limit 20"
```

### `review-resolve`

Назначение:
вручную подтвердить или отклонить ambiguous match.

Когда использовать:

- если `review-list` показал спорные кейсы.

Подтвердить:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-resolve --match-id 123 --resolution confirm_candidate --style-direction-id 456 --review-note 'Подтверждено вручную'"
```

Отклонить:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode review-resolve --match-id 123 --resolution reject_candidate --review-note 'Спорное совпадение отклонено'"
```

### `merge`

Назначение:
создать контролируемую связь legacy `style_directions` и канонических `styles`.

Когда использовать:

- после `match`;
- после разруливания ambiguous cases.

Что делает:

- берёт только безопасные match-решения;
- не должен перетирать manual-решения;
- формирует link-layer между legacy и canonical.

Dry-run:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode merge --dry-run --merge-limit 20"
```

Реальный запуск:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode merge --merge-limit 20"
```

### `run-list`

Назначение:
операторский мониторинг batch-run.

Когда использовать:

- посмотреть текущие и последние прогоны;
- понять, что делает parser сейчас;
- найти run для `resume` или `abort`.

Что показывает:

- `run_status`
- `progress_percent`
- `remaining_count`
- `last_attempted_source_title`
- `last_error`
- `fatal_error`
- `resume_available`
- `abort_available`

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-list --run-limit 20"
```

### `run-abort`

Назначение:
аварийно остановить зависший batch-run.

Когда использовать:

- batch-run реально завис;
- нужно освободить source;
- нужно потом продолжить через `resume`.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-abort --run-id 123"
```

## 6. Рекомендуемые Сценарии Использования

Перед выбором сценария полезно ответить на один вопрос:

- вы хотите просто собрать знания о стилях из trusted source;
- или вы хотите, чтобы эти знания уже начали связываться с существующим каталогом сайта.

### Сценарий A. Проверить одну страницу

Подходит для smoke-test.

1. `alembic upgrade head`
2. `single`

### Сценарий B. Наполнить канонический parser-каталог по основному API-first пути

Подходит, если задача — именно загрузка знаний из trusted source и нужен текущий production-путь.

1. `enqueue-jobs`
2. `run-worker`

На этом этапе legacy `style_directions` можно вообще не трогать.

### Сценарий B2. Наполнить канонический parser-каталог через legacy/manual `batch`

Подходит, если нужно вручную прогнать ограниченный срез кандидатов старым совместимым способом.

1. `discover --dry-run`
2. `batch --dry-run`
3. `batch`
4. `run-list`

### Сценарий C. Связать parser-каталог с каталогом сайта

Подходит, если canonical parser-данные должны начать работать в продукте.

1. `enqueue-jobs`
2. `run-worker`
3. `match --dry-run`
4. `match`
5. `review-list`
6. `review-resolve`
7. `merge --dry-run`
8. `merge`

## 7. Как Запустить Parser И Забыть

Если говорить совсем просто, сейчас есть три режима эксплуатации:

- основной API/job-driven режим: оператор делает `enqueue-jobs`, а дальше запускает штатный `run-worker`;
- ручной режим: оператор сам запускает `single`, `discover`, `process-next-job`, `match`, `review`, `merge` по ситуации;
- legacy/manual режим: оператор использует `batch` и внешний offset-loop для совместимого старого запуска.

### Важное ограничение legacy `batch`

Сейчас `batch` обрабатывает только один срез списка кандидатов:

- `offset`
- `limit`

То есть одной команды вида `--mode batch --limit 10` недостаточно, чтобы “обойти весь источник до конца”.

Если всё же нужен legacy `batch`-режим “запустить и забыть”, безопасный вариант на сегодня — внешний shell-цикл, который:

1. запускает очередной `batch`;
2. ждёт его завершения;
3. делает паузу;
4. увеличивает `offset`;
5. повторяет цикл.

### Foreground-вариант для legacy `batch`

Пачка по `10`, пауза `5` минут:

```bash
bash -lc '
set -e
offset=0
while true; do
  out=$(docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --offset $offset --limit 10")
  echo "$out"
  selected=$(printf "%s" "$out" | python3 -c "import sys,json; print(json.load(sys.stdin)[\"selected_count\"])")
  [ "$selected" -eq 0 ] && break
  offset=$((offset + 10))
  sleep 300
done
'
```

### Background-вариант для legacy `batch`

Если нужно оставить процесс жить после закрытия SSH-сессии:

```bash
nohup bash -lc '
set -e
offset=0
while true; do
  out=$(docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --offset $offset --limit 10")
  echo "$out"
  selected=$(printf "%s" "$out" | python3 -c "import sys,json; print(json.load(sys.stdin)[\"selected_count\"])")
  [ "$selected" -eq 0 ] && break
  offset=$((offset + 10))
  sleep 300
done
' > ~/style_ingestion_batch.log 2>&1 &
```

### Основной API/job-driven вариант

Сначала discovery в очередь:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode enqueue-jobs --limit 50"
```

Важно:

- `enqueue-jobs` теперь ставит отдельную `discover_source_pages` job
- discovery уже выполняется worker-ом, а не inline внутри команды
- если страница уже сохранена в той же revision, новый detail fetch не ставится
- при новой revision ставится новый `fetch_style_page` job

Потом штатный worker:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-worker --worker-max-jobs 101 --worker-stop-when-idle"
```

Важно:

- для свежей очереди на `N` style pages безопасный job-budget считать как `1 + 2N`
  - `1` discovery job
  - до `N` fetch jobs
  - до `N` normalize jobs
- для `limit 50` разумный `worker-max-jobs` это `101`
- `run-worker` теперь сам requeue-ит retryable API/fetch jobs вместо мгновенного финального `soft_failed`
- `run-worker` теперь сам reclaim-ит stale `running` jobs после рестарта worker/container
- `cooldown_deferred` остаётся отдельным статусом, когда source уже ушёл в `cooldown`
- финальный `soft_failed` теперь означает, что retry budget исчерпан или ошибка не считается retryable
- именно этот путь сейчас считается основным operational запуском parser-а

### Как следить за таким прогоном

Через `run-list`:

```bash
watch -n 5 'docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-list --run-limit 10"'
```

Или без `watch`:

```bash
while true; do
  clear
  docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-list --run-limit 10"
  sleep 5
done
```

### Когда использовать `resume-run-id`

`resume-run-id` нужен не для обхода всего источника по кускам.
Он нужен только для продолжения одного уже прерванного batch-run.

Пример:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode batch --resume-run-id 123"
```

## 8. Как Читать Результаты

### Что значит `created_count`

Это количество реально новых записей в каноническом parser-слое.

### Что значит `updated_count`

Это не ошибка.
Это значит, что parser обработал стиль повторно и обновил уже существующую запись.

Обычно это происходит, если:

- запускали `batch` по тому же `offset`;
- страница уже была загружена раньше;
- изменились поля и parser переписал existing style/source snapshot.

### Что значит `failed_count`

Это число кандидатов в текущем batch, которые не смогли пройти pipeline.

### Статусы batch-run

- `running` — run ещё идёт
- `completed` — run завершён без ошибок
- `completed_with_failures` — run завершён, но часть кандидатов упала
- `failed` — run аварийно оборвался
- `aborted` — run остановлен оператором

## 9. Что Делать Нельзя

- не запускать parser локально на Windows-хосте вместо Docker
- не запускать большой `batch` сразу на сотни страниц
- не запускать два `batch`-run одновременно для одного source
- не считать `resume-run-id` заменой внешнего offset-loop
- не пропускать `review-list / review-resolve`, если есть ambiguous matches
- не использовать `review-resolve` как dry-run: этот режим записывает решение

## 10. Короткая Памятка

Если задача “быстро проверить parser”:

1. `alembic upgrade head`
2. `single` или `discover --dry-run`

Если задача “наполнить knowledge base”:

1. `enqueue-jobs`
2. `run-worker`

Если задача “связать parser-каталог с каталогом сайта”:

1. `enqueue-jobs`
2. `run-worker`
3. `match --dry-run`
4. `match`
5. `review-list`
6. `review-resolve`
7. `merge --dry-run`
8. `merge`

Если задача “запустить и забыть”:

1. использовать `enqueue-jobs`
2. запускать `run-worker`
3. мониторить через `run-list`
3. при зависании использовать `run-abort`
