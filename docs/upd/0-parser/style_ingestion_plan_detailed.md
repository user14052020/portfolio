[Как пользоваться в style_ingestion_operations.md](./style_ingestion_operations.md) 

Парсер уже задуман как отдельный ingestion pipeline, а не как часть чата: в docs есть отдельный parser contour, каталоги raw/normalized/logs, проверка robots.txt, cron-обновления и принцип “сначала собрать и нормализовать каталог, потом уже использовать его в чате”.  ￼

Для именно этого донора я бы не делал ставку на HTML-скрапинг обычных страниц. Aesthetics Wiki — это wiki со структурированными осями навигации (By Category, By Family, By Color, By Decade, By Country) и большой A–Z-страницей, а MediaWiki для таких сайтов предоставляет api.php, включая получение wikitext, parsed HTML и других метаданных через Action API. Это куда более устойчивый путь, чем тащить куки браузера и биться с edge-защитой HTML-страниц.  ￼

Мой вывод такой: куки/localStorage не делать базовой архитектурой. Их можно использовать только как временную диагностическую меру, если тебе нужно сравнить “что видит браузер” и “что получает бот”, но не как основной production-путь. Правильная архитектура — это:
	1.	index fetcher по A–Z и taxonomy-страницам,
	2.	detail fetcher по API,
	3.	raw store,
	4.	normalizer/extractor,
	5.	upsert в knowledge БД,
	6.	retry/circuit-breaker/logging.  ￼

Вот план уровня senior-архитектуры, чтобы парсер грузил базу мягко и без сбоев.

1. Перестроить fetcher: HTML only → API first

Для Fandom/MediaWiki основным источником должен стать не обычный page HTML, а API-режимы:
	•	action=query&prop=revisions...rvprop=content для сырого wikitext,
	•	action=parse&page=...&prop=text для parsed HTML.
Это стандартный путь MediaWiki для чтения страниц программно.  ￼

Что это даст:
	•	меньше шансов словить пустой HTML от фронтовой защиты;
	•	меньше мусора: баннеры, ads, shell-разметка;
	•	более стабильные поля для нормализации;
	•	можно хранить revision id и обновлять только изменившиеся страницы.  ￼

2. Разделить pipeline на 3 независимых джобы

Не один “батч на N страниц”, а три контура:

A. Discovery job
Берёт:
	•	A–Z список,
	•	family/category/color/decade/country страницы,
	•	внутренние ссылки на style pages.
На самой wiki эти оси уже явно присутствуют, поэтому их нужно использовать как отдельные источники классификации, а не только как навигацию для человека.  ￼

B. Detail fetch job
По очереди забирает каждую style page через API и сохраняет:
	•	page_title
	•	page_id
	•	revision_id
	•	fetched_at
	•	raw_wikitext
	•	parsed_html
	•	raw_sections
	•	raw_links

C. Normalize/enrich job
Отдельно, без похода в сеть:
	•	выделяет summary;
	•	палитру, garments, materials, silhouettes, moods;
	•	связи со стилями;
	•	family/category/color/decade/country;
	•	пишет в нормализованные таблицы.

Это прямо продолжает тот separation-of-concerns, который уже заложен в docs репо: parser как отдельный контур, а не часть chat request.  ￼

3. Ввести polite crawling policy

Если HTML сейчас иногда пустой, это может быть soft mitigation, challenge page или нестабильный edge-ответ. Не стоит “ломать” это куками. Нужна мягкая политика:
	•	1 активный worker на source;
	•	rate limit не по “батчу”, а между HTTP-запросами;
	•	случайный jitter;
	•	exponential backoff на пустое тело / 403 / 429 / 5xx;
	•	circuit breaker: после серии пустых ответов источник ставится на cooldown;
	•	retry budget на страницу, не бесконечный.

Практически:
	•	старт: 1 запрос в 20–40 секунд;
	•	jitter ±30%;
	•	после пустого HTML: пауза 15–30 минут;
	•	после 3–5 подряд пустых ответов: стоп source до ручной проверки.

Это намного лучше, чем просто “раз в 5 минут батчем 5 штук”, потому что protection часто реагирует не только на интервал, а на сам паттерн и тип endpoint.

4. Не использовать браузерные куки как основу

Cookies/localStorage я бы оценил так:
	•	для прод-архитектуры — нет;
	•	для диагностики — можно разово.

Почему:
	•	они быстро протухают;
	•	их сложно безопасно хранить;
	•	они привязывают ingestion к конкретному пользователю/браузеру;
	•	это резко ухудшает воспроизводимость и масштабируемость.

Исключение одно: если ты докажешь, что API или HTML без валидной сессии системно не работает, тогда можно делать manual cookie bootstrap, но всё равно как временный bridge, а не как главный путь.

5. Перейти на source-state machine

У каждого source должна быть таблица состояния.

Например source_fetch_state:
	•	source_id
	•	mode (active, cooldown, blocked_suspected, maintenance)
	•	last_success_at
	•	last_empty_body_at
	•	consecutive_empty_bodies
	•	last_http_status
	•	last_error_class
	•	next_allowed_at
	•	current_min_interval_sec

Тогда парсер не “молотит батчи”, а ведёт себя как сервис:
	•	успешный fetch → уменьшить интервал до базового;
	•	пустой ответ → повысить интервал;
	•	серия ошибок → cooldown.

6. Сохранять raw response целиком

Сейчас тебе не хватает диагностики. Для каждого fetch нужно хранить:
	•	URL
	•	method
	•	status code
	•	headers
	•	response size
	•	content-type
	•	body hash
	•	первые N KB body
	•	fetch mode (html, api_parse, api_revisions)
	•	latency

Потому что “пустой HTML” — это ещё не диагноз. Это может быть:
	•	challenge shell,
	•	truncated response,
	•	anti-bot placeholder,
	•	bad gzip,
	•	redirect loop,
	•	другая страница без контента.

Пока ты не логируешь headers/body fingerprint, ты лечишь вслепую.

7. Делать обновления по revision/page fingerprint, а не по тупому re-fetch

Для wiki это особенно важно. Через API можно опираться на:
	•	pageid,
	•	title,
	•	revision id,
	•	content hash.  ￼

Тогда:
	•	если revision не изменился — detail re-fetch не нужен;
	•	normalize/enrich запускается только на изменившихся страницах;
	•	нагрузка резко падает.

8. Использовать taxonomy страницы как cheap knowledge multiplier

На Aesthetics Wiki уже есть полезные оси:
	•	category,
	•	family,
	•	color,
	•	decade,
	•	country.  ￼

Их нужно парсить отдельно и сохранять как:
	•	taxonomy_nodes
	•	style_taxonomy_links

Это даст тебе сильный эффект в продукте:
	•	“Попробовать другой стиль” → выбрать соседний стиль из той же family, но с другой color/decade axis;
	•	“Подобрать к вещи” → матчить не по сырому названию, а по silhouette/material/color family;
	•	“Что надеть на событие” → подмешивать occasion-fit через style profile и relations.

9. Добавить очередь и idempotent jobs

Если проект должен масштабироваться и жить долго, fetch не должен идти “одним скриптом”.

Нужны:
	•	таблица ingest_jobs
	•	таблица source_pages
	•	таблица source_page_versions
	•	таблица ingest_attempts

Каждая job:
	•	идемпотентна;
	•	может быть безопасно перезапущена;
	•	пишет чёткий статус (queued, running, succeeded, soft_failed, hard_failed, cooldown_deferred).

Это полностью соответствует направлению repo docs, где parser задуман как отдельный ingestion pipeline с cron, raw/normalized слоями и не-real-time обновлением.  ￼

10. Что я бы сделал прямо сейчас

Самый рациональный порядок:
	1.	Оставить существующий парсер, но добавить fetch abstraction
	•	MediaWikiApiFetcher
	2.	Для aesthetics.fandom.com переключить source на:
	•	Discovery via MediaWiki API
	•	Detail via MediaWiki API
	3.	Добавить таблицу source_fetch_state


    НЕ ПЕРЕПИСЫВАЕМ ВЕСЬ ПАРСЕР А переводим его на работу с публичным API

    после завершения всех работ по данному плану актуализируем C:\dev\portfolio\docs\upd\style_ingestion_operations.md

Статус реализации на 2026-04-09:
    - discovery для `aesthetics_wiki` идёт через MediaWiki Action API, включая taxonomy discovery pages;
    - detail fetch идёт через MediaWiki Action API;
    - runtime fetch policy использует `source_fetch_state`;
    - `source_pages/source_page_versions/ingest_jobs/ingest_attempts` подключены в рабочий job-driven pipeline;
    - discovery переведен в first-class job `discover_source_pages`, то есть pipeline теперь буквально трехступенчатый: `discovery -> detail fetch -> normalize/enrich`;
    - discovery/taxonomy pages сохраняются как first-class `source_pages/source_page_versions`;
    - detail snapshots сохраняют `raw_wikitext`, `parsed_html`, `raw_text`, `raw_sections`, `raw_links`.
    - HTML fetch/fallback contour из runtime parser-а удален; сетевой путь для `aesthetics_wiki` теперь API-only.
    - taxonomy discovery pages теперь реально участвуют в canonical taxonomy: их section-aware snapshots и DOM-context taxonomy groups подмешиваются в `style_taxonomy_links` при normalize шага style page;
    - worker умеет reclaim-ить stale `running` jobs после рестарта контейнера или процесса, поэтому очередь стала операционно перезапускаемой.
    - `run-worker` и `process-next-job` теперь берут source-level DB lease c heartbeat и TTL через `style_source_fetch_states`, поэтому у source одновременно активен только один worker-процесс.
