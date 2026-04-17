
# Полный план доработки style enrichment, runtime-ограничений, admin settings и chat UI  
## Без полной замены текущей логики parser / ingestion  
## Для Cursor / implementation use  
## С учётом OOP, SOLID, FSD, чистоты кода, масштабируемости и удобства поддержки

## 0. Назначение документа

Этот документ фиксирует **обновлённый, полный и развёрнутый scope реализации**, который заменяет более тяжёлый вариант полной переработки parser pipeline.

### Новое решение:
Мы **не переписываем текущий parser целиком**.  
Вместо этого поверх уже существующей логики добавляется **отдельный enrichment-слой**, который:

1. берёт **исходный текст стиля из базы**;
2. отправляет этот текст в **ChatGPT**;
3. получает обратно **нужные structured JSON blocks**;
4. раскладывает их по **новым специализированным таблицам**;
5. позволяет использовать enriched данные:
   - для **текстовой консультации**,
   - для **генерации картинки**,
   - для **пояснения стиля рядом с результатом генерации**.

Дополнительно в этот же scope входят:

6. ограничение для пользователей, которые **не админы**:
   - не более **5 генераций в день**,
   - не более **10 минут текстового чата в день**;
7. эти ограничения должны **меняться из админки**;
8. cooldown после отправки сообщения:
   - **60 секунд**;
9. cooldown после `Попробовать другой стиль`:
   - тоже **60 секунд**;
10. эти cooldown-настройки тоже должны **меняться из админки**;
11. chat UI должен получить мягкий premium-вид:
   - все элементы скруглённые,
   - круглый loader/countdown вместо обычной send button,
   - чёрный фон + белая круглая заполняющаяся полоска в send control.

Этот документ опирается на исходную проблему, зафиксированную в `style_ingestion_semantic_distillation_plan_v2.md`: текущий parser слишком грубо схлопывает style source text и теряет данные, критичные и для stylist consultation, и для image generation. Но теперь вместо полного parser rewrite мы идём более прагматичным путём — добавляем **LLM enrichment over stored source text**. fileciteturn21file0

---

# 1. Executive summary

## 1.1. Что именно меняется
### Мы оставляем:
- текущий style ingestion pipeline;
- текущий source-layer;
- текущий canonical style creation;
- текущий coarse profile generation;
- текущие parser jobs.

### Мы добавляем:
- отдельный enrichment script / enrichment service;
- новые enriched tables;
- ChatGPT extraction over DB source text;
- runtime consumption enriched data;
- style explanation near generation result;
- admin-configurable quotas;
- admin-configurable cooldown;
- rounded chat UI;
- circular cooldown control.

---

## 1.2. Что мы НЕ делаем
### Мы НЕ делаем:
- полный rewrite `style_feature_extractor.py`;
- полный rewrite `style_feature_catalog.py`;
- полный replacement of existing ingestion jobs;
- тяжёлую parser migration before runtime improvements;
- обязательный vocabulary v2 refactor по всему ingestion ядру;
- обязательный replacement of all legacy style profile fields.

---

## 1.3. Почему это правильный scope сейчас
Потому что он:
- даёт практический результат быстрее;
- не ломает working ingestion foundation;
- позволяет использовать уже сохранённые исходники из БД;
- снижает риск regression;
- создаёт основу для будущего перехода к richer architecture без экстренной перестройки всего parser слоя.

---

# 2. Новый главный архитектурный принцип

## 2.1. Parser остаётся, enrichment добавляется сверху
Новая схема должна мыслиться так:

```text
Current parser / source ingestion stays
+
LLM enrichment layer over stored source text
```

---

## 2.2. Что это означает practically
### Existing parser отвечает за:
- source fetch
- source persistence
- canonical style rows
- coarse style profile
- taxonomy / relations baseline
- ingestion stability

### New ChatGPT enrichment отвечает за:
- richer stylistic knowledge
- richer image generation data
- richer visual language extraction
- better style explanation text
- downstream runtime enhancement

---

## 2.3. Почему это хорошо по архитектуре
Это соответствует принципу:
- не ломать working foundation;
- расширять систему additive way;
- вводить новые capabilities через отдельный слой;
- сохранять backward compatibility;
- уменьшать blast radius изменений.

---

# 3. Новый целевой pipeline

## 3.1. High-level схема

```text
Existing style source ingestion
→ raw style source saved in DB
→ canonical style + coarse profile saved

→ ChatGPT enrichment script
   → reads raw text from DB
   → builds structured extraction prompt
   → sends to ChatGPT
   → validates JSON
   → normalizes values
   → stores enriched records in DB

→ runtime
   → text consultation uses enriched knowledge
   → image generation uses enriched image/style data
   → generation result includes style explanation from DB
```

---

## 3.2. Почему именно так
Это даёт:
- быстрый practical upgrade;
- clean separation of concerns;
- возможность batch reprocessing;
- возможность dry-run / compare;
- отсутствие необходимости трогать fetch pipeline и source acquisition.

---

# 4. Почему нельзя продолжать только на current coarse parser output

Из исходного анализа уже видно, что current parser слишком рано схлопывает source text и теряет:
- styling rules;
- layered logic;
- visual treatment;
- props;
- composition cues;
- signature details;
- relation richness;
- better style explanation material. fileciteturn21file0

Если оставить всё как есть:
- text consultation будет бедной;
- generation prompts будут слишком общими;
- result cards не смогут объяснять, “что это за стиль” на хорошем уровне;
- future knowledge layer будет строиться на слабой базе.

---

# 5. Новый enrichment scope

## 5.1. Что должен делать enrichment
Enrichment должен превращать stored style source text в **несколько typed JSON blocks**, пригодных для runtime.

---

## 5.2. Что enrichment НЕ должен делать
Enrichment не должен:
- заменять canonical style identity;
- переписывать source pages;
- удалять old style profiles;
- ломать legacy relations;
- превращаться в единственный parser до того, как это отдельно решено.

---

# 6. Источник данных для enrichment

## 6.1. Enrichment работает только на already stored DB text
Приоритет источников:

1. `style_source_pages`
2. `style_source_sections`
3. `style_source_evidences` — только как optional supplement

---

## 6.2. Почему не API напрямую
Потому что:
- не нужен повторный fetch;
- меньше зависимости от донора;
- можно backfill’ить локально;
- проще повторять и отлаживать;
- стабильнее versioning.

---

## 6.3. Базовый принцип
> Enrichment reads from DB, not from donor API.

---

# 7. Почему именно ChatGPT как enrichment provider

## 7.1. Роль ChatGPT
ChatGPT используется здесь не как runtime brain, а как:
- semantic extractor
- JSON producer
- style enrichment engine for stored source text

---

## 7.2. Почему не локальный runtime vLLM
Текущий vLLM лучше оставить для runtime:
- routing
- reasoning
- dialogue

А extraction делегировать более сильной модели, потому что:
- это batch/non-realtime задача;
- здесь качество JSON и semantic structuring важнее локальности.

---

## 7.3. Архитектурное правило
Нужен provider abstraction, но на этом этапе default provider = **ChatGPT (OpenAI)**.

---

# 8. Какие JSON должен возвращать ChatGPT

## 8.1. Важно
Нельзя просить у модели один “большой комбайн JSON” без структуры.

Нужно получать **пачку логических JSON-блоков**.

---

## 8.2. Блок 1 — `StyleKnowledgeJson`
Для text consultation и reasoning.

```json
{
  "style_name": "2010s Soft Kawaii",
  "core_definition": "…",
  "core_style_logic": ["…"],
  "styling_rules": ["…"],
  "casual_adaptations": ["…"],
  "statement_pieces": ["…"],
  "status_markers": ["…"],
  "overlap_context": ["…"],
  "historical_notes": ["…"],
  "negative_guidance": ["…"]
}
```

---

## 8.3. Блок 2 — `StyleVisualLanguageJson`
Для visual reasoning, explanation и generation.

```json
{
  "palette": ["pink", "cream", "mint green", "brown"],
  "lighting_mood": ["warm"],
  "photo_treatment": ["slight sepia", "soft instagram-like look"],
  "visual_motifs": ["kawaii mascots", "sweets", "stickers"],
  "patterns_textures": ["florals", "swiss dots", "herringbone"],
  "platform_visual_cues": ["Tumblr", "Instagram"]
}
```

---

## 8.4. Блок 3 — `StyleFashionItemsJson`
Для richer outfit reasoning.

```json
{
  "tops": [...],
  "bottoms": [...],
  "shoes": [...],
  "accessories": [...],
  "hair_makeup": [...],
  "signature_details": [...]
}
```

---

## 8.5. Блок 4 — `StyleImagePromptAtomsJson`
Для generation.

```json
{
  "hero_garments": [...],
  "secondary_garments": [...],
  "core_accessories": [...],
  "props": [...],
  "materials": [...],
  "composition_cues": [...],
  "negative_constraints": [...],
  "visual_motifs": [...],
  "lighting_mood": [...],
  "photo_treatment": [...]
}
```

---

## 8.6. Блок 5 — `StyleRelationsJson`
Для relation-aware reasoning и future graph.

```json
{
  "related_styles": [...],
  "overlap_styles": [...],
  "preceded_by": [...],
  "succeeded_by": [...],
  "brands": [...],
  "platforms": [...],
  "origin_regions": [...],
  "era": [...]
}
```

---

## 8.7. Блок 6 — `StylePresentationJson`
Для generation result explanation.

```json
{
  "short_explanation": "…",
  "one_sentence_description": "…",
  "what_makes_it_distinct": ["…", "…", "…"]
}
```

Этот блок нужен специально для UI — чтобы рядом с генерацией можно было показать короткое пояснение о стиле.

---

# 9. Какие таблицы нужно добавить

## 9.1. Общий принцип
Новые enriched данные нужно хранить **рядом**, а не пытаться запихнуть всё в старые поля `style_profiles`.

---

## 9.2. Таблица `style_llm_enrichments`
Для audit trail LLM run.

Поля:
- `id`
- `style_id`
- `source_page_id`
- `provider`
- `model_name`
- `prompt_version`
- `schema_version`
- `status`
- `raw_response_json`
- `error_message`
- `created_at`

---

## 9.3. Таблица `style_knowledge_facets`
Для text consultation.

Поля:
- `id`
- `style_id`
- `facet_version`
- `core_definition`
- `core_style_logic_json`
- `styling_rules_json`
- `casual_adaptations_json`
- `statement_pieces_json`
- `status_markers_json`
- `overlap_context_json`
- `historical_notes_json`
- `negative_guidance_json`
- `updated_at`

---

## 9.4. Таблица `style_visual_facets`
Для visual language.

Поля:
- `id`
- `style_id`
- `facet_version`
- `palette_json`
- `lighting_mood_json`
- `photo_treatment_json`
- `visual_motifs_json`
- `patterns_textures_json`
- `platform_visual_cues_json`
- `updated_at`

---

## 9.5. Таблица `style_fashion_item_facets`
Для inventory-like style structure.

Поля:
- `id`
- `style_id`
- `facet_version`
- `tops_json`
- `bottoms_json`
- `shoes_json`
- `accessories_json`
- `hair_makeup_json`
- `signature_details_json`
- `updated_at`

---

## 9.6. Таблица `style_image_facets`
Для generation.

Поля:
- `id`
- `style_id`
- `facet_version`
- `hero_garments_json`
- `secondary_garments_json`
- `core_accessories_json`
- `props_json`
- `materials_json`
- `composition_cues_json`
- `negative_constraints_json`
- `visual_motifs_json`
- `lighting_mood_json`
- `photo_treatment_json`
- `updated_at`

---

## 9.7. Таблица `style_relation_facets`
Поля:
- `id`
- `style_id`
- `facet_version`
- `related_styles_json`
- `overlap_styles_json`
- `preceded_by_json`
- `succeeded_by_json`
- `brands_json`
- `platforms_json`
- `origin_regions_json`
- `era_json`
- `updated_at`

---

## 9.8. Таблица `style_presentation_facets`
Для generation result explanation.

Поля:
- `id`
- `style_id`
- `facet_version`
- `short_explanation`
- `one_sentence_description`
- `what_makes_it_distinct_json`
- `updated_at`

---

# 10. Почему отдельные таблицы лучше, чем обновлять `style_profiles`

Потому что:
- меньше риск сломать legacy runtime;
- можно rollout делать постепенно;
- можно версионировать enrichment independently;
- можно хранить audit of LLM runs;
- проще сделать backfill и compare;
- reasoning и generation смогут постепенно переключаться на новые данные.

---

# 11. Новый enrichment script: обязанности

## 11.1. Новый script должен уметь
- read one style by `style_id`
- read multiple styles by ids
- run batch by filter
- run full backfill
- dry-run without writing
- retry failed styles
- overwrite existing facets optional
- skip already enriched styles default

---

## 11.2. Новый application service
Рекомендуется создать:

```python
class StyleChatGptEnrichmentService(Protocol):
    async def enrich_style(self, style_id: int) -> StyleEnrichmentResult:
        ...
```

---

## 11.3. Batch runner
```python
class StyleChatGptEnrichmentBatchRunner(Protocol):
    async def run(
        self,
        *,
        style_ids: list[int] | None = None,
        limit: int | None = None,
        offset: int = 0,
        dry_run: bool = False,
        overwrite_existing: bool = False,
    ) -> BatchEnrichmentResult:
        ...
```

---

# 12. ChatGPT extraction flow

## 12.1. Пайплайн одного style enrichment run

```text
load style raw source from DB
→ build cleaned text payload
→ build extraction prompt
→ call ChatGPT
→ parse JSON
→ validate schema
→ normalize values
→ write facet tables
→ log enrichment run
```

---

## 12.2. Важно: не отправлять в модель мусорный giant dump как есть
Перед вызовом ChatGPT нужен lightweight preprocessing:
- concatenate relevant source text
- remove obvious navigation garbage if already known
- trim repeated blocks
- keep section titles if available

Но это не rewrite parser logic — это просто prompt hygiene.

---

# 13. Validation layer обязателен

## 13.1. Нельзя доверять raw JSON модели
Нужны typed schemas.

Рекомендуется Pydantic models:
- `StyleKnowledgePayload`
- `StyleVisualLanguagePayload`
- `StyleFashionItemsPayload`
- `StyleImagePayload`
- `StyleRelationsPayload`
- `StylePresentationPayload`

---

## 13.2. Что делать при invalid JSON
- retry once or twice
- write failed enrichment log
- do not partially corrupt current records
- do not silently swallow error

---

# 14. Runtime usage enriched data

## 14.1. Где enriched data начинает использоваться
После записи новых facet tables runtime должен уметь читать их:

### Для консультаций:
- `style_knowledge_facets`
- `style_visual_facets`
- `style_fashion_item_facets`
- `style_relation_facets`

### Для generation:
- `style_image_facets`
- `style_visual_facets`
- `style_presentation_facets`

---

## 14.2. Что менять в reasoning
Reasoning layer должен читать richer structured knowledge через provider / assembler и использовать это для:
- stylist advice
- clearer explanations
- better `FashionBrief`

---

## 14.3. Что менять в generation
Generation pipeline должен использовать:
- image facets
- visual facets
- fashion item facets
- profile alignment
- negative constraints

---

# 15. Пояснение о стиле рядом с генерацией

## 15.1. Новое продуктовое требование
Когда показывается результат генерации, нужно рядом вывести:

- **название стиля**
- **короткое пояснение, что это за стиль**
- **немного текста о нём из базы**

---

## 15.2. Откуда брать текст
Приоритет:
1. `style_presentation_facets.short_explanation`
2. `style_presentation_facets.one_sentence_description`
3. fallback: `style_knowledge_facets.core_definition`
4. fallback: existing `style_profiles.visual_summary` / `fashion_summary`

---

## 15.3. Где показывать это в UI
Рекомендуемый UI pattern:
- under generated image
- or in side info card / expandable info block
- with title + 2–4 short lines max

---

## 15.4. Почему это важно
Это:
- повышает ощущение “умного продукта”;
- объясняет пользователю, что он видит;
- связывает consultation и generation;
- делает style system понятнее.

---

# 16. Ограничения для не-админа

## 16.1. Новое правило
Если пользователь **не админ**:

- максимум **5 генераций в день**
- максимум **10 минут текстового чата в день**

---

## 16.2. Почему это отдельный слой
Это не parser concern и не UI concern.  
Это:
- runtime policy
- access governance
- abuse control
- cost control

---

## 16.3. Новый сервис
```python
class UsageAccessPolicyService(Protocol):
    async def evaluate(self, subject: UserContext, action: RequestedAction) -> UsageDecision:
        ...
```

---

## 16.4. Новые сущности
```python
class UsageQuota:
    daily_generation_limit: int
    daily_chat_seconds_limit: int

class UsageDecision:
    is_allowed: bool
    denial_reason: str | None
    remaining_generations: int
    remaining_chat_seconds: int
```

---

# 17. Почему лимиты должны меняться из админки

## 17.1. Нельзя хардкодить
Если лимиты зашить в код:
- придётся делать redeploy for simple config change;
- невозможно быстро адаптировать продукт;
- неудобно тестировать different operational policies.

---

## 17.2. Значит нужны admin-configurable settings
Нужно хранить в БД настройки типа:

- `daily_generation_limit_non_admin`
- `daily_chat_seconds_limit_non_admin`
- `chat_cooldown_seconds`
- `style_retry_cooldown_seconds`

---

# 18. Новая таблица/модель настроек

## 18.1. Если already есть `site_settings`
Рекомендуется использовать существующий settings subsystem и добавить новые keys.

---

## 18.2. Рекомендуемые ключи
- `stylist_chat.daily_generation_limit_non_admin`
- `stylist_chat.daily_chat_seconds_limit_non_admin`
- `stylist_chat.message_cooldown_seconds`
- `stylist_chat.try_other_style_cooldown_seconds`

---

## 18.3. Если нужна typed service
```python
class StylistRuntimeSettingsService(Protocol):
    async def get_limits(self) -> StylistRuntimeLimits:
        ...
```

```python
class StylistRuntimeLimits:
    daily_generation_limit_non_admin: int
    daily_chat_seconds_limit_non_admin: int
    message_cooldown_seconds: int
    try_other_style_cooldown_seconds: int
```

---

# 19. Cooldown policy

## 19.1. Что требуется
После:
- отправки любого сообщения
- нажатия `Попробовать другой стиль`

чат должен блокироваться на **60 секунд**  
(или другое значение из админки).

---

## 19.2. Важно
Cooldown должен быть:
- и на frontend,
- и на backend

Frontend-only нельзя — это обходится.

---

## 19.3. Новый backend сервис
```python
class InteractionThrottleService(Protocol):
    async def can_submit(self, user_id: str, action_type: str) -> ThrottleDecision:
        ...
```

---

## 19.4. Новый frontend behavior
- send control заменяется на circular countdown
- input disabled
- quick action disabled
- `Попробовать другой стиль` disabled until cooldown ends

---

# 20. Rounded chat UI

## 20.1. Новое требование
Все элементы чата должны стать визуально мягче:
- rounded surfaces
- rounded input
- rounded controls
- rounded message bubbles
- rounded action pills

---

## 20.2. Почему это отдельно важно
Это не просто cosmetic tweak:
- ощущение продукта меняется;
- интерфейс становится premium / calmer;
- better fit for stylist assistant product.

---

# 21. Новый send control

## 21.1. Вместо обычной кнопки
Нужен новый control:

- круглый
- чёрная подложка
- белая круглая заполняющаяся полоска
- 60-second countdown

---

## 21.2. Новый shared/frontend компонент
Рекомендуется:

`ChatCooldownSendControl`

Props:
- `isLocked`
- `secondsRemaining`
- `onSubmit`
- `disabledReason`
- `variant`

---

## 21.3. Этот же control / похожая логика должна работать после `Попробовать другой стиль`

---

# 22. Что менять в админке

## 22.1. Нужен раздел настроек runtime policy
В админке должен быть UI для редактирования:

- max generations/day for non-admin
- max chat seconds/day for non-admin
- message cooldown seconds
- try-other-style cooldown seconds

---

## 22.2. Рекомендуемый admin UI
В existing settings/admin section добавить отдельный блок:

### `Stylist Chat Runtime Settings`
Поля:
- `Daily generation limit (non-admin)`
- `Daily text chat duration limit, seconds (non-admin)`
- `Message cooldown, seconds`
- `Try other style cooldown, seconds`

С кнопкой:
- Save settings

---

## 22.3. Что важно
Admin UI должен:
- показывать current values;
- валидировать minimum/maximum ranges;
- не позволять negative values;
- писать изменения в DB settings store.

---

# 23. Что менять во frontend по FSD

## 23.1. Shared
`src/shared/ui`
- `ProgressRing`
- `SoftButton`
- `RoundIconButton`
- `InputSurface`

`src/shared/api`
- types for runtime settings
- settings fetch/update

---

## 23.2. Entities
- `entities/usage-policy`
- `entities/chat-cooldown`
- `entities/stylist-runtime-settings`

---

## 23.3. Features
- `features/send-message`
- `features/style-exploration-trigger`
- `features/chat-cooldown`
- `features/admin-stylist-runtime-settings`

---

## 23.4. Widgets
- update `widgets/stylist-chat-panel`
- update composer
- update generation result card
- update settings/admin widgets

---

# 24. Что менять во backend по слоям

## 24.1. Models / DB
Добавить:
- `style_llm_enrichments`
- `style_knowledge_facets`
- `style_visual_facets`
- `style_fashion_item_facets`
- `style_image_facets`
- `style_relation_facets`
- `style_presentation_facets`

И использовать existing settings store or add typed keys.

---

## 24.2. Repositories
Создать:
- `style_llm_enrichments.py`
- `style_knowledge_facets.py`
- `style_visual_facets.py`
- `style_fashion_item_facets.py`
- `style_image_facets.py`
- `style_relation_facets.py`
- `style_presentation_facets.py`

---

## 24.3. Services
Создать:
- `StyleChatGptEnrichmentService`
- `StyleChatGptEnrichmentBatchRunner`
- `StylistRuntimeSettingsService`
- `UsageAccessPolicyService`
- `InteractionThrottleService`

---

## 24.4. API
Нужны:
- admin endpoint to trigger enrichment
- admin endpoint to read/update stylist runtime settings
- runtime endpoint(s) should respect access policy and throttle
- generation response DTO should include style explanation data

---

# 25. Как использовать enriched data в текстовой консультации

## 25.1. Reasoning layer должен читать enriched style knowledge
Reasoning и knowledge layer должны использовать:
- `core_style_logic`
- `styling_rules`
- `casual_adaptations`
- `historical_notes`
- `overlap_context`
- `negative_guidance`
- `palette`
- `signature details`

---

## 25.2. Это нужно для:
- более точных советов
- лучшего объяснения why the outfit works
- richer stylistic answers
- better CTA to visualization

---

# 26. Как использовать enriched data в generation

## 26.1. Generation layer должен читать:
- `hero_garments`
- `secondary_garments`
- `core_accessories`
- `props`
- `materials`
- `composition_cues`
- `negative_constraints`
- `visual_motifs`
- `lighting_mood`
- `photo_treatment`

---

## 26.2. Это нужно для:
- более точного flat lay
- более контролируемой картинки
- меньшего generic output
- лучшей style recognizability

---

# 27. Обратная совместимость

## 27.1. Runtime не должен падать, если enrichment для стиля ещё не прогнан
Нужен fallback:
1. enriched facets if present
2. legacy profile fields if no enriched facets
3. minimal safe response if neither available

---

## 27.2. Почему это важно
Потому что enrichment будет запускаться постепенно.

---

# 28. Observability

## 28.1. Что логировать
Для enrichment runs:
- style_id
- source_page_id
- provider
- model
- prompt_version
- schema_version
- success/failure
- validation status
- write status

Для runtime limits:
- allowed / denied
- remaining generations
- remaining chat seconds
- cooldown active / not active

---

## 28.2. Почему это важно
Без этого невозможно:
- дебажить enrichment quality
- понимать, почему response бедный
- понимать, почему user заблокирован по лимиту/cooldown

---

# 29. Тестирование

## 29.1. Unit tests
Нужны на:
- JSON validation
- enrichment normalization
- settings service
- usage access policy
- throttle service

---

## 29.2. Integration tests
Сценарии:
- style enrichment writes all facet tables
- enrichment fallback on invalid JSON
- runtime consultation uses enriched knowledge
- generation uses enriched image data
- generation explanation text renders
- non-admin quotas enforced
- cooldown enforced
- admin settings change applied

---

## 29.3. Product tests
Проверить:
- richer style consultations
- better generation consistency
- style explanation appears near image
- limits really configurable via admin
- cooldown control visually works and server also blocks spam

---

# 30. Clean Architecture / SOLID / OOP

## 30.1. Domain layer
- typed payload schemas
- facet entities
- usage quota entities
- throttle entities
- runtime settings entities

## 30.2. Application layer
- enrichment service
- batch runner
- settings service
- usage access policy
- throttle policy

## 30.3. Infrastructure layer
- OpenAI client
- repositories
- settings persistence
- migrations
- logging

## 30.4. Interface layer
- admin endpoints
- frontend settings forms
- chat cooldown UI
- generation explanation rendering

---

## 30.5. SRP
Каждый сервис делает одну вещь:
- enrichment
- validation
- settings read/write
- quota evaluation
- throttle evaluation
- UI rendering

---

## 30.6. OCP
Можно позже:
- заменить ChatGPT provider;
- расширить JSON schema;
- менять limits/cooldown ranges;
- добавлять новые facet tables

без переписывания core runtime.

---

## 30.7. DIP
Runtime reasoning и generation должны зависеть не от raw DB tables напрямую, а от:
- typed facet repositories / provider interfaces
- settings service
- policy services

---

# 31. Пошаговый план реализации

## Подэтап 1. Добавить новые facet tables и migration
- LLM enrichment log
- knowledge facets
- visual facets
- fashion item facets
- image facets
- relation facets
- presentation facets

## Подэтап 2. Реализовать ChatGPT enrichment service
- load source from DB
- prompt builder
- model call
- JSON validation
- write to DB

## Подэтап 3. Реализовать batch/backfill runner
- single style
- batch
- dry run
- skip existing
- overwrite mode

## Подэтап 4. Подключить enriched data в runtime
- consultation path
- generation path
- fallback logic

## Подэтап 5. Добавить generation style explanation
- backend DTO
- frontend rendering

## Подэтап 6. Реализовать runtime settings layer
- DB-backed settings
- admin update UI
- typed settings service

## Подэтап 7. Реализовать non-admin limits
- generation/day
- chat time/day
- backend enforcement

## Подэтап 8. Реализовать cooldown
- backend throttle
- frontend countdown ring
- disable send and try-other-style

## Подэтап 9. Rounded UI polish
- composer
- buttons
- bubbles
- chips
- surfaces

## Подэтап 10. Observability and tests
- logs
- metrics
- unit tests
- integration tests
- product tests

---

# 32. Acceptance criteria

Этап считается завершённым, если:

1. Текущий parser не переписан целиком и не сломан.
2. Есть отдельный enrichment script/service, который читает исходный текст из БД.
3. Enrichment отправляет текст в ChatGPT и получает structured JSON.
4. JSON валидируется и раскладывается по отдельным таблицам.
5. Эти данные реально используются:
   - в текстовой консультации
   - в генерации изображения
6. При генерации рядом показывается пояснение о стиле из базы.
7. Для не-админа работают лимиты:
   - 5 generations/day
   - 10 minutes chat/day
8. Эти лимиты меняются из админки.
9. Cooldown после send и after `Попробовать другой стиль` работает.
10. Cooldown значение меняется из админки.
11. Chat UI стал rounded и использует круговой loader/countdown.
12. Есть fallback, если enrichment ещё не прогнан.
13. Архитектура остаётся чистой и расширяемой.

---

# 33. Definition of Done

Работа считается завершённой корректно, если:
- проект получил richer style knowledge без полного parser rewrite;
- новый enrichment layer реально усилил и консультации, и генерацию;
- generation results стали объяснимее за счёт style explanation;
- quotas и cooldown управляются из админки;
- UX стал мягче и современнее;
- backend enforcement защищает от обхода UI ограничений;
- решение не создаёт архитектурного хаоса и остаётся пригодным для дальнейшего масштабирования.

---

# 34. Архитектурный итог

После реализации этого плана проект получает:

## В ingestion/data layer
- существующий parser остаётся стабильной базой;
- поверх него появляется ChatGPT-based enrichment layer;
- richer style data хранится в отдельных tables.

## В runtime
- текстовая консультация становится умнее;
- generation становится точнее;
- рядом с generation появляется понятное объяснение стиля.

## В product policy
- non-admin usage ограничивается;
- cooldown и quotas контролируются централизованно;
- settings меняются без redeploy через админку.

## В UI
- chat становится мягче и premium;
- interaction выглядит продуманной, а не технической.

И это даёт проекту реальное улучшение качества без лишней тяжёлой работы по полной замене существующего parser ядра.
