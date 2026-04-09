# Доменный Контракт Ingestion-Слоя Стилей

Обновлено: 2026-04-09

## Назначение

Этот документ фиксирует минимальный доменный контракт ingestion-слоя по [style_ingestion_plan.md](/c:/dev/portfolio/docs/upd/style_ingestion_plan.md), чтобы дальнейшая реализация шла по шагам и без смешивания parser-логики с chat runtime.

## Архитектурные Границы

- ingestion-слой существует отдельно от chat runtime;
- parser не живет внутри conversational backend;
- ingestion запускается как отдельный процесс, cron или worker;
- chat backend читает только готовые нормализованные данные, но не занимается парсингом источников;
- сырой источник, нормализованные признаки и связи между стилями хранятся раздельно.

## Центральные Слои Модели

### 1. Слой Источников

Нужен для хранения страницы стиля "как есть" и повторной переработки без повторного обхода сайта.

Минимальные сущности:

- `style_sources`
- `style_source_sections`
- `style_source_links`
- `style_source_images`

Минимальные поля источника:

- `source_url`
- `source_site`
- `source_title`
- `fetched_at`
- `last_seen_at`
- `source_hash`
- `raw_html`
- `raw_text`
- `raw_sections_json`
- `parser_version`
- `normalizer_version`

### 2. Каноническая Сущность Стиля

Это центральный объект, на который дальше опираются рекомендации, retrieval, анти-повтор и prompt building.

Минимальные сущности:

- `styles`
- `style_aliases`

Минимальные поля `styles`:

- `canonical_name`
- `slug`
- `display_name`
- `status`
- `source_primary_id`
- `short_definition`
- `long_summary`
- `confidence_score`
- `first_ingested_at`
- `updated_at`

Минимальные поля `style_aliases`:

- `style_id`
- `alias`
- `alias_type`
- `language`
- `is_primary_match_hint`

### 3. Нормализованные Признаки

Это слой, который делает знания о стиле пригодными для чата и генерации.

Минимальные сущности:

- `style_profiles`
- `style_traits`

Задачи слоя:

- хранить краткую итоговую карточку стиля;
- хранить атомарные признаки для поиска, сравнения и анти-повтора;
- хранить source evidence для объяснимости.

### 4. Связи И Таксономия

Это слой осмысленных переходов между стилями.

Минимальные сущности:

- `style_taxonomy_nodes`
- `style_taxonomy_links`
- `style_relations`

Назначение слоя:

- controlled difference для команды "попробовать другой стиль";
- стилевые мостики и соседства;
- навигация по семействам, категориям, эпохам, цветам и регионам.

### 5. Audit И История Обновлений

Это слой наблюдаемости ingestion-процесса.

Минимальные сущности:

- `style_ingest_runs`
- `style_ingest_changes`

Задачи слоя:

- фиксировать запуск ingestion;
- логировать обновленные стили;
- хранить информацию о конфликтах матчинга и изменениях полей.

## Компоненты Parser/Ingestion

Компоненты, которые должны появляться в коде поэтапно:

- `style_source_registry`
- `style_scraper`
- `style_normalizer`
- `style_enricher`
- `style_validator`
- `style_db_writer`

## Порядок Реализации

Чтобы не смешивать уровни ответственности, реализация идет в таком порядке:

1. Зафиксировать доменный контракт ingestion-слоя.
2. Создать source-layer модели и миграции.
3. Создать canonical style-layer модели и миграции.
4. Создать profile/traits-layer модели и миграции.
5. Создать taxonomy/relation-layer модели и миграции.
6. Создать audit-layer модели и миграции.
7. Только после фиксации модели начинать собирать parser pipeline.

## Что Не Делаем На Этом Шаге

- не пишем scraper "вперед структуры БД";
- не смешиваем ingestion с chat runtime;
- не создаем произвольный pipeline до фиксации доменных сущностей;
- не привязываем реализацию к одному текстовому bootstrap-источнику как к финальной архитектуре.
