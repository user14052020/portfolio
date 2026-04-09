Да — это лучше оформить как **отдельный ingestion/knowledge слой**, а не как “парсер в одну таблицу”. На самой Aesthetics Wiki есть не только A–Z список, но и дополнительные оси навигации: **по категории, семейству, цвету, десятилетию и региону**, а сами страницы эстетик описывают стиль через моду, музыку, интерьер, искусство и другие медиумы. Это как раз подсказывает правильную структуру БД: отдельно хранить **каноническую сущность стиля**, отдельно **сырой источник**, отдельно **нормализованные признаки**, отдельно **связи стиль↔стиль** и **стиль↔теги/оси классификации**. ([aesthetics.fandom.com][1])

Я бы разбил это на 4 слоя.

## 1. Слой источников: сохраняем страницу “как есть”

Нужно забирать со страницы стиля **не только описание**, а весь полезный контент, который потом можно переразобрать без повторного парсинга сайта.

### Что сохраняем из каждой страницы

* `source_url`
* `source_site` = `aesthetics.fandom.com`
* `source_title`
* `fetched_at`
* `last_seen_at`
* `source_hash` — хеш сырого HTML/очищенного текста
* `raw_html`
* `raw_text`
* `raw_sections_json` — секции статьи после первичного разбиения
* `parser_version`
* `normalizer_version`

### Зачем это нужно

* можно перепарсить старые данные новым парсером без повторного обхода сайта;
* можно видеть, когда страница реально изменилась;
* можно хранить несколько версий разбора одной и той же страницы.

---

## 2. Каноническая сущность `style`

Это главный объект, на который потом будет опираться чат-бот.

### Таблица `styles`

Поля:

* `id`
* `canonical_name`
* `slug`
* `display_name`
* `status` (`draft`, `active`, `deprecated`, `alias_only`)
* `source_primary_id`
* `short_definition`
* `long_summary`
* `confidence_score`
* `first_ingested_at`
* `updated_at`

### Таблица `style_aliases`

Поля:

* `id`
* `style_id`
* `alias`
* `alias_type` (`exact`, `spelling`, `community_name`, `legacy_name`, `db_import_name`)
* `language`
* `is_primary_match_hint`

### Зачем это нужно

У тебя уже есть почти тысяча названий в базе. Их нельзя тупо джойнить по строке 1:1. Нужны:

* алиасы,
* нормализация,
* ручное подтверждение спорных совпадений,
* сохранение исходного имени из твоей базы отдельно от канонического имени на сайте.

---

## 3. Нормализованные признаки стиля

Это ключевой слой для того, чтобы бот **думал структурно**, а не пересказывал сырой текст.

### Таблица `style_profiles`

Одна актуальная нормализованная карточка на стиль.

Поля:

* `style_id`
* `essence` — краткая суть стиля
* `fashion_summary`
* `visual_summary`
* `historical_context`
* `cultural_context`
* `mood_keywords_json`
* `color_palette_json`
* `materials_json`
* `silhouettes_json`
* `garments_json`
* `footwear_json`
* `accessories_json`
* `hair_makeup_json`
* `patterns_textures_json`
* `seasonality_json`
* `occasion_fit_json`
* `negative_constraints_json`
* `styling_advice_json`
* `image_prompt_notes_json`

### Таблица `style_traits`

Нормализованные признаки в long-form виде.

Поля:

* `id`
* `style_id`
* `trait_type`
* `trait_value`
* `weight`
* `source_evidence_id`

Примеры `trait_type`:

* `color`
* `material`
* `silhouette`
* `garment`
* `footwear`
* `accessory`
* `motif`
* `era`
* `region`
* `subculture`
* `art_reference`
* `mood`
* `occasion`
* `composition_hint`

### Почему так лучше, чем один JSON

`style_profiles` удобен для быстрого чтения ботом, а `style_traits` удобен для:

* поиска похожих стилей,
* анти-повтора,
* фильтрации,
* рекомендаций,
* аналитики.

---

## 4. Связи между стилями

На сайте стили явно группируются не только по алфавиту, но и по **семействам, цветам, эпохам, категориям и регионам**. Эти оси очень полезны для твоего сценария генерации и рекомендаций. ([aesthetics.fandom.com][1])

### Таблица `style_taxonomy_nodes`

Поля:

* `id`
* `taxonomy_type` (`family`, `category`, `color`, `decade`, `region`, `umbrella_term`)
* `name`
* `slug`
* `description`

### Таблица `style_taxonomy_links`

Поля:

* `style_id`
* `taxonomy_node_id`
* `link_strength`
* `source_evidence_id`

### Таблица `style_relations`

Поля:

* `id`
* `source_style_id`
* `target_style_id`
* `relation_type`
* `score`
* `reason`
* `source_evidence_id`

`relation_type`:

* `same_family`
* `subcategory_of`
* `inspired_by`
* `adjacent_to`
* `shares_palette_with`
* `shares_silhouette_with`
* `historically_related`
* `contrast_pair`
* `fusion_candidate`

### Почему это важно

Именно это даст боту возможность:

* не повторять один и тот же образ;
* делать “попробовать другой стиль” не случайно, а **с контролируемым отличием**;
* строить мостики между стилями осмысленно.

---

# Что именно забирать со страницы стиля

Я бы делал так: при обходе A–Z списка парсер заходит на каждую страницу найденного стиля и сохраняет:

### 1. Базовые метаданные

* заголовок страницы
* URL
* дата парсинга
* хеш документа
* оглавление/список секций

### 2. Основной текст по секциям

Нужно сохранять **каждую секцию отдельно**, а не только слитный текст.

Таблица `style_source_sections`:

* `source_page_id`
* `section_order`
* `section_title`
* `section_level`
* `section_text`
* `section_hash`

### 3. Внутренние ссылки со страницы

Таблица `style_source_links`:

* `source_page_id`
* `anchor_text`
* `target_title`
* `target_url`
* `link_type` (`wiki_internal`, `external`, `taxonomy_hint`, `see_also`)

### 4. Изображения

Даже если сначала не используешь их в модели, лучше хранить метаданные:

* `image_url`
* `caption`
* `alt_text`
* `position`
* `license_if_available`

Это пригодится потом для:

* визуального embedding поиска,
* moodboard preview,
* ручной валидации стиля.

---

# Как нормализовать текст

После загрузки сырого контента делай отдельный этап нормализации.

## Pipeline

1. **Fetch**

   * получаем страницу из списка A–Z;
   * валидируем, что страница соответствует стилю из твоей БД.

2. **Extract**

   * вытаскиваем title, sections, internal links, images, raw text.

3. **Normalize**

   * чистим мусор;
   * объединяем разорванные абзацы;
   * сохраняем структуру секций;
   * приводим имена признаков к единому словарю.

4. **Feature extraction**

   * извлекаем:

     * палитру,
     * ткани,
     * силуэты,
     * вещи,
     * обувь,
     * аксессуары,
     * эпоху,
     * mood,
     * культурные и художественные референсы,
     * “чего избегать”.

5. **Linking**

   * привязываем стиль к:

     * семейству,
     * категории,
     * цветовым и историческим осям,
     * соседним стилям.

6. **Persist**

   * обновляем канонический `style`;
   * записываем версию профиля;
   * логируем источник и дату обновления.

7. **Audit**

   * пишем в ingest log:

     * что обновили,
     * какие поля изменились,
     * confidence,
     * были ли конфликты матчинга.

---

# Как лучше связать таблицы

Вот рациональная схема:

* `styles` — центральная сущность
* `style_aliases` — альтернативные названия
* `style_sources` — источник страницы
* `style_source_sections` — сырой текст по секциям
* `style_profiles` — итоговая карточка
* `style_traits` — атомарные признаки
* `style_taxonomy_nodes` — семейства/цвета/эпохи/регионы
* `style_taxonomy_links` — связи с осями
* `style_relations` — связи стиль↔стиль
* `style_ingest_runs` — логи парсинга
* `style_ingest_changes` — диффы по изменениям

Такой дизайн хорош тем, что:

* можно перерабатывать признаки независимо от сырого текста;
* можно дообогащать базу другими источниками позже;
* можно строить рекомендации и генерацию без повторного парсинга.

---

# Как это использовать в твоем чат-боте

## 1. “Попробовать другой стиль”

Вместо того чтобы просто брать новый `style_name`, бот делает так:

* загружает текущий стиль и его `style_traits`;
* ищет **соседние стили** по `style_relations`;
* исключает стили с пересечением по тем же:

  * палитрам,
  * силуэтам,
  * ключевым вещам;
* выбирает стиль, который:

  * относится к той же широкой семье,
  * но отличается по минимум 2–3 главным признакам.

### Пример

Текущий стиль:

* `Dark Academia`

Бот может предложить:

* не снова темный пиджак + лоферы,
* а уйти в `Light Academia` или `Art School`,
* при этом сменить:

  * палитру,
  * ткани,
  * тип обуви,
  * уровень формальности.

---

## 2. “Подобрать к вещи”

Если пользователь пишет:
“темно-синяя джинсовая рубашка”

Бот:

* извлекает вещь и её параметры;
* ищет стили, где такая вещь или близкий материал/силуэт типичны;
* строит outfit не из общего вкуса модели, а из `style_traits` и `styling_advice`.

### Пример

Для вещи “джинсовая рубашка” система может:

* найти стили, где `denim`, `workwear`, `western`, `minimal casual`, `americana` имеют высокий вес;
* предложить 2–3 stylistic directions;
* дальше собрать prompt для flat lay уже с учетом **подтвержденного style profile**.

---

## 3. “Что надеть на событие”

Если пользователь пишет:

* “на выставку современного искусства”,

бот:

* матчится не только по dress code, но и по стилям, у которых в `cultural_context` и `occasion_fit` есть близкие сигналы;
* выбирает 1–2 стилевых направления;
* добавляет цветовую и композиционную логику.

### Пример

Для выставки современного искусства:

* опора на стили с признаками:

  * `minimalism`,
  * `art-school`,
  * `avant-garde light`,
  * `gallery-core`;
* плюс отдельный слой color logic, где можно использовать твои будущие заметки по Малевичу.

---

## 4. Обычный стилистический чат

Бот перестает “фантазировать от головы” и начинает отвечать на основе:

* `style_profiles`,
* `style_traits`,
* `style_relations`,
* будущих лекционных/теоретических заметок.

Это и есть путь к образу “историк моды + портной + color theorist”, а не просто “LLM с хорошим тоном”.

---

# Несколько удачных примеров использования именно в твоем контексте

## Пример A. Анти-повтор в генерации

Сохраняем у предыдущей генерации:

* palette = `camel, navy, cream`
* silhouette = `tailored`
* garments = `blazer, pleated trousers, loafers`

При следующем `try another style`:

* система ищет стиль из той же смысловой зоны,
* но исключает пересечение по этим признакам,
* и генерирует, например:

  * `washed olive, charcoal, off-white`
  * `relaxed silhouette`
  * `overshirt, wide trousers, derbies`

---

## Пример B. Мостики между стилями

Пользователь любит `Cottagecore`, но хочет что-то “чуть современнее”.

Через `style_relations` бот может предложить:

* `Cottagecore → Farmcore → Soft Naturalist → Meadow Kei`

Не случайный ответ, а понятный стилевой переход.

---

## Пример C. Подбор вокруг вещи

Пользователь пишет:

* “есть бордовая юбка миди”

Система:

* матчит вещь по `garment + color + silhouette`;
* ищет стили, где бордовый и миди-силуэт типичны;
* выдает 2 направления:

  * романтическое,
  * интеллектуально-артистическое;
* потом собирает два разных flat lay prompt.

---

## Пример D. Генерация эстетичных prompt-ов

Из `style_profile` в prompt уходят не “общие слова”, а:

* palette,
* fabric family,
* silhouette,
* accessory logic,
* artistic reference,
* scene composition hints,
* negative constraints.

Тогда картинка становится не просто “красивая flat lay”, а stylistically grounded.

---

# Что логировать обязательно

Таблица `style_ingest_runs`:

* `id`
* `started_at`
* `finished_at`
* `source_name`
* `source_url`
* `styles_seen`
* `styles_matched`
* `styles_created`
* `styles_updated`
* `styles_failed`
* `parser_version`
* `normalizer_version`

Таблица `style_ingest_changes`:

* `run_id`
* `style_id`
* `change_type`
* `field_name`
* `old_value_hash`
* `new_value_hash`
* `change_summary`

Это поможет поддерживать проект в будущем, когда у тебя будет уже не один источник и не тысяча, а несколько тысяч карточек.

---

# Практический принцип

Лучше мыслить так:

* **не парсим “описание стиля”**
* а строим **style knowledge graph**

То есть:

* стиль,
* признаки,
* оси классификации,
* связи с другими стилями,
* рекомендации,
* доказательства из источника.

И уже поверх этого строятся:

* чат,
* команды,
* prompt builder,
* анти-повтор,
* retrieval.


[1]: https://aesthetics.fandom.com/wiki/List_of_Aesthetics "List of Aesthetics | Aesthetics Wiki | Fandom"
