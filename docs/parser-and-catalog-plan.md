# Parser And Catalog Plan

## Цель

Собирать товары с локальных сайтов секондов и показывать пользователю те вещи, которые реально дополняют его образ.

## Главный принцип

Parser не должен работать "по запросу чата" в реальном времени.

Правильная схема:

1. Parser периодически собирает данные.
2. Данные нормализуются и попадают в локальный каталог.
3. Чат уже ищет по готовому каталогу.

Иначе будут:

- долгие ответы;
- бан по rate limit;
- нестабильность;
- разъезд UX и data quality.

## Источники данных

Для каждого сайта нужен отдельный adapter:

- `source_name`
- `city / region`
- `listing_url`
- `product_url`
- `title`
- `description`
- `price`
- `currency`
- `brand`
- `size`
- `condition`
- `category`
- `color`
- `material`
- `image_urls`
- `availability`
- `collected_at`

## Что нужно хранить в базе

### Offers

- [ ] source_id
- [ ] external_id
- [ ] url
- [ ] title_raw
- [ ] description_raw
- [ ] normalized_category
- [ ] normalized_subcategory
- [ ] normalized_colors
- [ ] normalized_style_tags
- [ ] normalized_gender_target
- [ ] size_text
- [ ] price
- [ ] currency
- [ ] brand
- [ ] condition
- [ ] city
- [ ] is_available
- [ ] first_seen_at
- [ ] last_seen_at

### Offer images

- [ ] offer_id
- [ ] original_url
- [ ] local_cached_url или storage key
- [ ] sort_order

### Matching metadata

- [ ] embeddings
- [ ] visual tags
- [ ] style tags
- [ ] silhouette tags
- [ ] season tags
- [ ] occasion tags

## Pipeline

### Stage 1. Fetch

- [ ] Снять список категорий и карточек.
- [ ] Собирать новые и обновлять существующие офферы.
- [ ] Не качать одни и те же страницы бесконечно.

### Stage 2. Normalize

- [ ] Привести категории к единому словарю.
- [ ] Привести цвета к единому словарю.
- [ ] Определить тип вещи:
  - top;
  - bottom;
  - outerwear;
  - shoes;
  - bag;
  - accessory.
- [ ] Выделить атрибуты из title и description.

### Stage 3. Enrich

- [ ] Сгенерировать visual tags.
- [ ] Сгенерировать embeddings.
- [ ] При необходимости прогнать vision model по картинке.
- [ ] Выделить признаки:
  - minimal;
  - vintage;
  - sporty;
  - classic;
  - streetwear;
  - feminine;
  - masculine;
  - oversized;
  - fitted.

### Stage 4. Match

- [ ] На вход получить structured recommendation от LLM.
- [ ] Подобрать вещи по категориям.
- [ ] Отфильтровать по конфликтующим цветам и стилям.
- [ ] Отранжировать по:
  - совместимости;
  - качеству картинки;
  - наполненности карточки;
  - новизне;
  - цене.

## Как бот должен использовать каталог

Бот не должен просто сыпать ссылками.

Он должен:

- коротко объяснить, почему вещь подходит;
- показывать 1-2 ключевых аргумента;
- давать 3-8 релевантных вариантов;
- уметь разделять:
  - "бюджетный вариант";
  - "самый стильный";
  - "самый безопасный";
  - "более смелый".

## Как связать это с LLM

LLM должен возвращать структурированный объект, например:

```json
{
  "intent": "style_recommendation_with_catalog",
  "main_item": "black oversized blazer",
  "tone": "sharp",
  "style_direction": ["smart casual", "minimal"],
  "recommended_slots": [
    "trousers",
    "shoes",
    "bag",
    "accessory"
  ],
  "avoid": [
    "too sporty",
    "neon colors"
  ],
  "preferred_colors": [
    "charcoal",
    "cream",
    "silver"
  ]
}
```

Это уже можно матчить с локальным каталогом без магии.

## Риски

- нестабильная разметка сайтов;
- отсутствие API;
- дубликаты товаров;
- плохие картинки;
- неполные данные по размерам;
- юридические ограничения на scraping.

## Что проверить до старта парсинга

- [ ] robots.txt
- [ ] rate limits
- [ ] terms of use
- [ ] частоту обновления
- [ ] нужно ли использовать прокси

## MVP parser scope

На первом этапе:

- 1-2 сайта;
- 3-5 категорий;
- только изображения и текст карточек;
- без сложного real-time sync;
- обновление по cron.

## Definition of Done

Парсер считается готовым к MVP, если:

- хотя бы один источник стабильно обновляется;
- каталог хранит нормализованные карточки;
- чат умеет показать подборку реальных вещей;
- пользователь понимает, почему именно эти вещи рекомендованы.
