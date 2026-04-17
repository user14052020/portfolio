
# Этап 4. Profile Context  
## Обновлённый подробный план реализации profile context для fashion chatbot  
## С учётом `style_ingestion_semantic_distillation_plan_v2` и обновлённого Этапа 3 (Reasoning pipeline)

## 0. Назначение документа

Этот документ является **полноценной обновлённой версией Этапа 4** и заменяет прежнюю редакцию `4-profile_context.md` в рамках нового roadmap, где между Routing redesign и Reasoning pipeline уже добавлен отдельный этап `style_ingestion_semantic_distillation_plan_v2`.

Цель этого обновления:

- не строить profile context как “позднюю косметическую настройку поверх генерации”;
- встроить profile context в runtime как **обязательный вход reasoning pipeline**;
- сделать profile context совместимым с richer parser output:
  - style advice facets
  - style image facets
  - style visual language facets
  - semantic-distilled style knowledge;
- не допустить повторной переделки profile logic после полной интеграции parser upgrade и knowledge layer;
- сохранить clean architecture, расширяемость, OOP-подход и пригодность к поддержке на больших масштабируемых проектах.

После parser upgrade и обновлённого Этапа 3 profile context больше не может проектироваться только как “добавка к prompt builder”. Он должен стать полноценной частью fashion-domain runtime pipeline.

---

# 1. Контекст и причина обновления

## 1.1. Что изменилось в общей архитектуре

Изначально этап Profile Context задумывался как важный runtime-блок, который:
- хранит presentation / silhouette / fit / comfort preferences;
- прокидывается в reasoning и generation;
- делает бота менее усреднённым.

Но после добавления `style_ingestion_semantic_distillation_plan_v2` ситуация изменилась:

теперь у системы появляется richer structured style knowledge:
- semantic fragments;
- advice-oriented style facets;
- image-oriented style facets;
- visual language facets;
- richer style relation data.

Это означает, что profile context должен:
- не просто передаваться в reasoning;
- а **пересекаться с richer style facets до reasoning**,
- чтобы reasoner работал уже не на “общем стиле”, а на стиле, выровненном под конкретного пользователя.

---

## 1.2. Почему старая логика Этапа 4 уже недостаточна

Старая редакция Этапа 4 правильно фиксировала:
- модель `presentation_profile`;
- `ProfileContextService`;
- хранение в localStorage и backend session;
- мягкую clarifications policy;
- обязательное участие profile context в reasoning и generation.

Но в новой архитектуре этого уже недостаточно, потому что не было детально описано:

- как profile context должен пересекаться с **semantic-distilled style facets**;
- как он должен влиять на выбор hero garments;
- как он должен участвовать в selection между style advice facets и image facets;
- как он должен встроиться в anti-repeat и diversity;
- как избежать размазывания profile-specific logic по reasoner, prompt builder и frontend.

Следовательно, профильный слой нужно обновить так, чтобы он стал **межслойным alignment-механизмом**, а не просто набором пользовательских полей.

---

# 2. Цель этапа

После реализации обновлённого Этапа 4 система должна:

1. Иметь явную, устойчивую и расширяемую модель profile context.
2. Уметь собирать и хранить профиль пользователя:
   - на frontend,
   - в session runtime,
   - при необходимости позже в persistent user profile.
3. Уметь мягко уточнять отсутствующие данные без тяжёлого onboarding.
4. Использовать profile context **до reasoning**, а не только в generation.
5. Уметь выравнивать retrieved style facets под конкретного пользователя.
6. Передавать в reasoning уже **profile-aligned style bundle**.
7. Формировать `FashionBrief` не “вообще”, а под подачу, силуэт, комфорт и формальность конкретного пользователя.
8. Оставаться устойчивой к отсутствию profile data.
9. Быть готовой к будущему расширению профиля без архитектурного слома.

---

# 3. Главный архитектурный принцип этапа

## 3.1. Profile context — это не “пол пользователя”

Нельзя продолжать мыслить profile как:

- `male`
- `female`

Это слишком грубо и продуктово неверно для fashion-domain системы.

Бот работает не с биологическим описанием человека, а с:
- подачей образа;
- силуэтом;
- степенью структурности / мягкости;
- уровнем комфорта;
- уровнем формальности;
- tolerances / avoidances.

Следовательно, новый принцип звучит так:

> **Profile Context = presentation-oriented stylistic user model**

---

## 3.2. Profile должен применяться до reasoning, а не только в generation

Это ключевое изменение версии 2.

### Было:
profile mostly → prompt builder / generation

### Должно стать:
profile → retrieval alignment → reasoning → FashionBrief → generation

Если profile применяется только в generation:
- советы остаются слишком общими;
- reasoning думает в абстракции;
- FashionBrief строится слишком поздно;
- часть персонализации запаздывает и становится менее естественной.

---

## 3.3. Profile Context не должен знать SQL и parser internals

Profile layer не должен зависеть от:
- таблиц parser pipeline;
- ORM моделей `style_*`;
- SQL-схемы knowledge layer.

Он должен работать на уровне:
- `ProfileContextSnapshot`
- `StyleFacetBundle`
- `ProfileAlignedStyleFacetBundle`

То есть через устойчивые доменные контракты.

---

# 4. Новая роль Profile Context в runtime pipeline

## 4.1. Обновлённая общая схема

```text
RoutingDecision
→ Retrieval profile selection
→ FashionReasoningContextAssembler
→ StyleFacetBundle
→ ProfileStyleAlignmentService
→ FashionReasoningInput
→ FashionReasoner
→ FashionReasoningOutput
→ VoiceLayerComposer
→ FinalResponse / FashionBrief / Generation handoff
```

---

## 4.2. Где именно profile участвует

Profile context участвует в пяти местах:

### 1. Clarification policy
Решает, нужно ли спросить про presentation / silhouette / formality.

### 2. Retrieval shaping
Подсказывает, какие style facets важнее.

### 3. Style alignment
Фильтрует и перевзвешивает style facet bundle.

### 4. Reasoning
Позволяет reasoner мыслить уже “для конкретного пользователя”.

### 5. Generation handoff
Передаёт нормализованные profile constraints в visual branch.

---

# 5. Что именно решает профильный слой

Обновлённый profile context должен помогать системе отвечать на такие вопросы:

- Для какой подачи собирать образ?
- Какие silhouettes усиливать или ослаблять?
- Нужно ли сделать образ более wearable?
- Нужно ли уменьшить декоративность?
- Какой уровень собранности уместен?
- Можно ли использовать statement pieces?
- Какие items лучше исключить?
- Какие фасоны и fit-решения лучше приоритетизировать?
- Какой вариант стиля подходит именно этому пользователю, а не “вообще”?

---

# 6. Новая структура Profile Context

## 6.1. Базовый состав профиля

Минимально необходимая структура:

- `presentation_profile`
- `fit_preferences`
- `silhouette_preferences`
- `comfort_preferences`
- `formality_preferences`
- `color_preferences`
- `color_avoidances`
- `preferred_items`
- `avoided_items`

---

## 6.2. `presentation_profile`

Допустимые базовые значения:

- `feminine`
- `masculine`
- `androgynous`
- `unisex`

Важно:
это не “кто пользователь”, а:
- в какой подаче лучше собирать образ;
- какой language of silhouette и garment logic применять.

---

## 6.3. `fit_preferences`

Примеры:
- `fitted`
- `relaxed`
- `oversized`
- `balanced`

---

## 6.4. `silhouette_preferences`

Примеры:
- `elongated`
- `soft`
- `structured`
- `minimal`
- `layered`
- `voluminous_top`
- `balanced_proportions`

---

## 6.5. `comfort_preferences`

Примеры:
- `high_comfort`
- `balanced`
- `style_first`

Это важно, потому что style advice facets часто содержат:
- более декоративные варианты;
- casual adaptations;
- more wearable adaptations.

Profile должен уметь на это реагировать.

---

## 6.6. `formality_preferences`

Примеры:
- `casual`
- `smart_casual`
- `refined`
- `formal`

Это влияет на:
- выбор advice facets;
- threshold на statement pieces;
- отрицательные ограничения в `FashionBrief`.

---

## 6.7. `color_preferences` и `color_avoidances`

Они нужны не только generation branch, но и reasoning:
- какие палитры рекомендовать;
- какие советы по сочетанию давать;
- какие style variants вообще предлагать.

---

## 6.8. `preferred_items` и `avoided_items`

Например:
- любит юбки
- не любит каблуки
- избегает слишком короткой длины
- предпочитает layering
- избегает крупных аксессуаров

Это особенно важно после parser upgrade, потому что richer style facets дают больше fine-grained garment signals, и profile должен уметь на них реагировать.

---

# 7. Расширяемость модели

## 7.1. Что не обязательно реализовывать сразу, но модель должна быть готова

- `footwear_preferences`
- `accessory_tolerance`
- `fabric_sensitivity`
- `body_focus_preferences`
- `seasonal_preferences`
- `climate_preferences`
- `wardrobe_constraints`
- `occasion_defaults`

---

## 7.2. Архитектурный принцип расширения

Новые profile fields должны:
- добавляться как расширение модели;
- не ломать `FashionReasoningInput`;
- не требовать переписывания reasoner;
- не тащить change cascade через весь runtime.

---

# 8. Новые доменные сущности

## 8.1. `PresentationProfile`

```python
class PresentationProfile(Enum):
    FEMININE = "feminine"
    MASCULINE = "masculine"
    ANDROGYNOUS = "androgynous"
    UNISEX = "unisex"
```

---

## 8.2. `ProfileContext`

```python
class ProfileContext:
    presentation_profile: PresentationProfile | None
    fit_preferences: list[str]
    silhouette_preferences: list[str]
    comfort_preferences: list[str]
    formality_preferences: list[str]
    color_preferences: list[str]
    color_avoidances: list[str]
    preferred_items: list[str]
    avoided_items: list[str]
```

---

## 8.3. `ProfileContextSnapshot`

Нужен immutable runtime snapshot:

```python
class ProfileContextSnapshot:
    presentation_profile: str | None
    fit_preferences: tuple[str, ...]
    silhouette_preferences: tuple[str, ...]
    comfort_preferences: tuple[str, ...]
    formality_preferences: tuple[str, ...]
    color_preferences: tuple[str, ...]
    color_avoidances: tuple[str, ...]
    preferred_items: tuple[str, ...]
    avoided_items: tuple[str, ...]
```

---

## 8.4. `ProfileAlignedStyleFacetBundle`

Нужен отдельный объект после alignment:

```python
class ProfileAlignedStyleFacetBundle:
    advice_facets: list[StyleAdviceFacet]
    image_facets: list[StyleImageFacet]
    visual_language_facets: list[StyleVisualLanguageFacet]
    relation_facets: list[StyleRelationFacet]
    alignment_notes: list[str]
```

Это помогает:
- не размазывать “что было до profile” и “что стало после profile”;
- упростить отладку;
- логировать quality decisions.

---

# 9. Новые сервисы профильного слоя

## 9.1. `ProfileContextService`

Это базовый application service, который отвечает за:
- чтение frontend hints;
- merge с session profile;
- merge с persistent profile (в будущем);
- валидацию и нормализацию;
- выдачу snapshot для pipeline.

```python
class ProfileContextService(Protocol):
    async def build_context(self, request: ProfileContextInput) -> ProfileContext:
        ...
    async def merge_updates(self, current: ProfileContext, updates: ProfileContextUpdate) -> ProfileContext:
        ...
    async def snapshot(self, profile: ProfileContext) -> ProfileContextSnapshot:
        ...
```

---

## 9.2. `ProfileContextNormalizer`

Нужен отдельный сервис, чтобы не тащить нормализацию в handlers или DTO.

Он должен:
- приводить значения к допустимым enum/list values;
- убирать дубликаты;
- отбрасывать неизвестные значения;
- нормализовать legacy payloads;
- ограничивать длину списков;
- обеспечивать совместимость старых и новых версий frontend payload.

---

## 9.3. `ProfileClarificationPolicy`

Этот сервис определяет:
- когда profile нужно уточнить;
- какое уточнение важнее;
- в каких сценариях можно не спрашивать;
- что делать, если profile incomplete.

```python
class ProfileClarificationPolicy(Protocol):
    async def evaluate(
        self,
        mode: str,
        profile: ProfileContextSnapshot | None,
        style_bundle: StyleFacetBundle | None,
    ) -> ProfileClarificationDecision:
        ...
```

---

## 9.4. Новый обязательный сервис: `ProfileStyleAlignmentService`

Это главное обновление Этапа 4.

```python
class ProfileStyleAlignmentService(Protocol):
    async def align(
        self,
        profile: ProfileContextSnapshot,
        style_facets: StyleFacetBundle
    ) -> ProfileAlignedStyleFacetBundle:
        ...
```

Он должен:
- фильтровать style facets;
- перевзвешивать их;
- усиливать релевантные;
- ослаблять конфликтующие;
- подготавливать aligned bundle для reasoner.

---

# 10. Что делает `ProfileStyleAlignmentService`

## 10.1. Фильтрация

Он должен уметь:
- убирать явно конфликтующие garments;
- ослаблять нерелевантные silhouettes;
- снижать вес неподходящих styling rules;
- исключать нежелательные footwear/accessory items.

Примеры:
- пользователь избегает каблуков → image/advice facets с heels получают lower weight;
- пользователь хочет more structured silhouette → слишком soft/romantic variants ослабляются;
- пользователь high-comfort → fragile/high-maintenance variants теряют приоритет.

---

## 10.2. Усиление

Он должен усиливать:
- presentation-relevant items;
- silhouette-compatible garments;
- comfort-consistent adaptations;
- formality-consistent variants;
- preferred items and colors.

---

## 10.3. Адаптация

Он должен уметь:
- превращать более editorial style variant в более wearable;
- переключать emphasis с decorative variant на casual adaptation;
- смягчать statement pieces;
- уменьшать риск “слишком красиво, но не носибельно”.

---

## 10.4. Weighting, а не только hard filtering

Очень важно:
profile alignment не должен быть только “запретить / разрешить”.

Нужно использовать:
- hard excludes
- soft penalties
- soft boosts

Иначе profile logic станет слишком жёсткой и будет ломать интересные stylistic решения.

---

# 11. Где profile alignment должен применяться

## 11.1. Не в prompt builder
Слишком поздно.

## 11.2. Не внутри reasoner
Иначе reasoner станет God-object.

## 11.3. Правильное место
Между:
- `FashionReasoningContextAssembler`
- и `FashionReasoner`

То есть pipeline выглядит так:

```text
assembler
→ style facet bundle
→ profile alignment
→ profile-aligned bundle
→ reasoner
```

Это самый чистый вариант архитектурно.

---

# 12. Влияние profile context на reasoning

## 12.1. Reasoner должен мыслить уже на aligned data

После обновления Этапа 4 reasoner не должен “догадываться”, что user likely prefers.

Он должен получать уже:
- filtered advice facets;
- filtered image facets;
- adjusted visual language signals.

---

## 12.2. Что это даёт

- меньше абстрактных советов;
- меньше усреднённости;
- больше ощущение “это подобрали мне”;
- более точный `FashionBrief`;
- меньше конфликтов между текстом и generation.

---

## 12.3. Какие части reasoning усиливаются

Profile alignment улучшает:
- garment selection;
- silhouette logic;
- negative constraints;
- CTA relevance;
- brief quality;
- anti-repeat diversification.

---

# 13. Влияние profile context на `FashionBrief`

## 13.1. `FashionBrief` должен содержать profile-derived decisions

Profile влияет на:
- `garment_list`
- `hero_garments`
- `silhouette`
- `accessories`
- `footwear`
- `negative_constraints`
- `composition_rules` (косвенно)
- `tailoring_logic`

---

## 13.2. Примеры

### Пример 1
Если user prefers:
- `presentation_profile = androgynous`
- `silhouette_preferences = structured, elongated`

то brief должен:
- меньше тянуться к overly romantic silhouette;
- сильнее удерживать clean vertical lines;
- меньше усиливать hyper-decorative accessory layer.

### Пример 2
Если user prefers:
- `comfort_preferences = high_comfort`
- `formality_preferences = smart_casual`

то brief должен:
- сильнее использовать casual adaptations;
- ослаблять fragile statement pieces;
- уменьшать сложность styling.

---

# 14. Влияние profile context на generation

## 14.1. Profile не должен заканчиваться на reasoning
После reasoning profile constraints должны продолжать жить в:
- `FashionBrief`
- `VisualGenerationPlan`
- prompt compilation
- generation safety / constraints policy

---

## 14.2. Но generation уже не должен быть первым местом применения profile
Это очень важное изменение.

Генерация должна использовать уже:
- profile-aware brief,
- а не пытаться “починить персонализацию в последний момент”.

---

# 15. Влияние profile context на retrieval

## 15.1. Profile может влиять даже раньше alignment
Не обязательно только фильтровать готовый bundle.  
Profile context может влиять ещё и на retrieval priorities.

Например:
- если user prefers androgynous structured silhouettes, retrieval может сильнее поднимать более relevant style bundles;
- если user strongly avoids heels, не нужно тянуть excessive heel-heavy image facets как top results.

---

## 15.2. Но важно не переусердствовать
Profile не должен:
- замыкать пользователя в слишком узком коридоре;
- превращать retrieval в “всегда одно и то же”.

Лучше:
- использовать profile как weighting signal;
- а не как абсолютный retriever gate.

---

# 16. Anti-repeat и profile context

## 16.1. Почему это важно
Даже profile-aware система может повторяться.

Например:
- один и тот же silhouette;
- одна и та же palette;
- один и тот же garment archetype.

---

## 16.2. Что должен знать профильный слой
Нужно уметь хранить:
- recently used style families;
- recently used palettes;
- recently recommended silhouettes;
- recently shown hero garments.

---

## 16.3. Где это хранится
Это не обязательно часть canonical user profile.  
Это лучше хранить как:
- session-level profile memory
- recent style interaction history

---

## 16.4. Как это использовать
Profile alignment должен:
- избегать скучных повторов;
- но сохранять верность user preferences.

То есть задача:
> **diverse within preference envelope**

---

# 17. Frontend storage и UX

## 17.1. Хранение на frontend

Profile context должен храниться в `localStorage`, чтобы:
- пользователь не повторял одно и то же;
- можно было постепенно собирать профиль;
- UI был continuity-friendly;
- soft clarifications не пропадали между refresh.

---

## 17.2. Что именно можно хранить на frontend
- last known `presentation_profile`
- silhouette preferences
- fit preferences
- comfort/formality hints
- optional avoidances

---

## 17.3. Backend session storage

Backend должен хранить:
- session profile context;
- merged normalized snapshot;
- recent profile-derived updates;
- profile completion state.

---

## 17.4. Двухуровневая схема обязательна
Потому что:
- frontend local storage важен для UX;
- backend session storage важен для reasoning consistency.

---

# 18. Persistent user profile (future-ready)

## 18.1. Не обязательно делать сразу
Но архитектура должна быть готова.

---

## 18.2. Что это даст позже
- долгосрочную персонализацию;
- меньше повторных уточнений;
- более точные stylistic trajectories;
- better style memory.

---

## 18.3. Важно
Persistent profile не должен ломать текущую session model.  
Он должен просто стать ещё одним источником merge в `ProfileContextService`.

---

# 19. Clarification policy

## 19.1. Почему profile нельзя выспрашивать тяжёлым onboarding
Это сломает UX.

---

## 19.2. Правильный подход
Profile должен собираться:
- постепенно;
- по делу;
- только когда это реально полезно;
- мягко и контекстно.

---

## 19.3. Примеры удачных вопросов
- “Под какую подачу собрать образ — более feminine, masculine, androgynous или универсальную?”
- “Есть ли предпочтение по силуэту — более мягкий, собранный или вытянутый?”
- “Хочешь, чтобы было максимально носибельно или можно чуть более выразительно?”

---

## 19.4. Когда задавать уточнение
Нужно, если:
- scenario реально зависит от profile;
- data insufficient for good brief;
- profile materially changes likely output.

Не нужно, если:
- можно безопасно ответить general way;
- clarification замедлит обычный диалог без явной пользы.

---

# 20. Интеграция с knowledge layer

## 20.1. Profile layer не должен зависеть от БД
Он должен работать через:
- `StyleFacetBundle`
- `KnowledgeContext`
- provider outputs

---

## 20.2. Почему это важно
Так:
- profile layer остаётся независимым;
- knowledge providers можно менять;
- parser schema можно развивать;
- reasoner остаётся стабильным.

---

## 20.3. Связка с `StyleDistilledKnowledgeProvider`
Когда Этап 5 будет обновлён, `StyleDistilledKnowledgeProvider` будет поставлять:
- advice facets;
- image facets;
- visual language facets;
- relation facets.

Profile layer должен быть готов принимать их уже как runtime-friendly contracts.

---

# 21. Новые application-level contracts

## 21.1. `ProfileContextInput`

```python
class ProfileContextInput:
    frontend_hints: dict[str, object] | None
    session_profile: ProfileContext | None
    persistent_profile: ProfileContext | None
    recent_updates: dict[str, object] | None
```

---

## 21.2. `ProfileContextUpdate`

```python
class ProfileContextUpdate:
    presentation_profile: str | None
    fit_preferences: list[str] | None
    silhouette_preferences: list[str] | None
    comfort_preferences: list[str] | None
    formality_preferences: list[str] | None
    color_preferences: list[str] | None
    color_avoidances: list[str] | None
    preferred_items: list[str] | None
    avoided_items: list[str] | None
```

---

## 21.3. `ProfileClarificationDecision`

```python
class ProfileClarificationDecision:
    should_ask: bool
    question_text: str | None
    missing_priority_fields: list[str]
```

---

# 22. Интеграция с orchestration layer

## 22.1. Где вызывается `ProfileContextService`
После:
- authentication/session resolution
- request payload normalization

До:
- retrieval
- reasoning
- generation handoff

---

## 22.2. Где вызывается `ProfileStyleAlignmentService`
После:
- `FashionReasoningContextAssembler`

До:
- `FashionReasoner`

---

## 22.3. Где используется snapshot
Во всех downstream слоях:
- reasoning input
- FashionBrief build
- generation plan
- logging/debug

---

# 23. Observability

## 23.1. Что логировать
Нужно логировать:
- profile completeness state
- profile clarifications asked / skipped
- alignment applied / not applied
- filtered facet counts
- boosted facet categories
- denied / removed item types
- final profile-derived constraints count

---

## 23.2. Почему это важно
Без этого нельзя понять:
- почему система выбрала такой образ;
- почему рекомендация вышла более casual / formal;
- почему CTA появилась / не появилась;
- почему response кажется пользователю “слишком общим”.

---

# 24. Тестирование

## 24.1. Unit tests
Нужны на:
- `ProfileContextNormalizer`
- `ProfileContextService`
- `ProfileClarificationPolicy`
- `ProfileStyleAlignmentService`

---

## 24.2. Integration tests
Нужны сценарии:
- no profile → safe general response
- partial profile → clarification
- strong profile → aligned reasoning
- profile affects `FashionBrief`
- profile affects generation constraints
- profile avoids repeated silhouettes

---

## 24.3. Product tests
Нужно проверять:
- advice feels more personal
- generation looks more aligned
- clarification is not annoying
- absence of profile does not break flow
- profile updates persist correctly

---

# 25. Clean Architecture / SOLID

## 25.1. Domain layer
- `ProfileContext`
- `ProfileContextSnapshot`
- `ProfileAlignedStyleFacetBundle`
- `ProfileClarificationDecision`

## 25.2. Application layer
- `ProfileContextService`
- `ProfileContextNormalizer`
- `ProfileClarificationPolicy`
- `ProfileStyleAlignmentService`

## 25.3. Infrastructure layer
- repositories for session profile / persistent profile
- localStorage payload adapters
- telemetry/logging

## 25.4. Interface layer
- frontend profile UI
- clarification UI
- API DTOs
- session middleware hooks

---

## 25.5. SOLID акценты

### SRP
- profile storage отдельно;
- normalization отдельно;
- clarification отдельно;
- style alignment отдельно.

### OCP
Новые profile fields должны добавляться расширением, а не переписыванием core services.

### DIP
Reasoner зависит от snapshot и aligned bundles, а не от DB и не от frontend payload.

---

# 26. Пошаговый план реализации

## Подэтап 1. Обновить domain contracts
- `ProfileContext`
- `ProfileContextSnapshot`
- `ProfileClarificationDecision`
- `ProfileAlignedStyleFacetBundle`

## Подэтап 2. Реализовать `ProfileContextNormalizer`
- normalization
- deduplication
- legacy compatibility

## Подэтап 3. Реализовать `ProfileContextService`
- merge local hints + session profile + future persistent profile
- snapshot output for pipeline

## Подэтап 4. Реализовать `ProfileClarificationPolicy`
- правила, когда задавать вопрос
- какой slot важнее
- when safe to skip

## Подэтап 5. Реализовать `ProfileStyleAlignmentService`
- hard excludes
- soft boosts / penalties
- profile-aligned facet bundle

## Подэтап 6. Протянуть profile context в runtime
- routing context hints
- reasoning input
- aligned style bundle
- `FashionBrief`
- generation plan

## Подэтап 7. Обновить frontend
- localStorage
- request payloads
- clarification UI
- profile patch updates

## Подэтап 8. Добавить observability и tests
- logs
- unit tests
- integration tests
- product tests

---

# 27. Acceptance criteria

Этап считается завершённым, если:

1. Profile context больше не применяется только на generation step.
2. Введена расширяемая модель `presentation_profile` и связанных preference fields.
3. Profile context хранится в `localStorage` и в backend session.
4. Profile context нормализуется и валидируется отдельными сервисами.
5. Profile clarification происходит мягко и контекстно.
6. Появился `ProfileStyleAlignmentService`.
7. Reasoning получает уже profile-aligned style bundle.
8. `FashionBrief` содержит profile-derived decisions.
9. Prompt / generation pipeline получает нормализованные profile constraints.
10. Отсутствие profile context не ломает runtime.
11. Архитектура готова к future persistent user profile.
12. Есть unit, integration и product tests.

---

# 28. Definition of Done

Этап реализован корректно, если:
- бот перестал быть “одинаковым для всех”;
- profile context стал обязательной частью runtime pipeline;
- reasoning начал работать не “вообще”, а под конкретную stylistic подачу пользователя;
- parser-upgraded style knowledge корректно выравнивается под профиль;
- рекомендации и визуализация стали заметно более релевантны;
- модель профиля остаётся расширяемой и не требует архитектурного слома при добавлении новых preference fields.

---

# 29. Архитектурный итог этапа

После реализации обновлённого Этапа 4 система получает не просто набор пользовательских настроек, а полноценный **profile-alignment layer** внутри fashion-domain runtime.

Это означает, что дальше:
- routing сможет понимать, когда профиль надо уточнить;
- retrieval и reasoning смогут выбирать не просто хороший стиль, а хороший стиль **для этого пользователя**;
- generation будет получать уже более точный, profile-aware `FashionBrief`;
- knowledge layer и voice layer будут работать поверх реального, а не усреднённого пользователя.

Именно это превращает profile context из второстепенной настройки в **обязательный доменный слой персонализации** для масштабируемого fashion reasoning assistant.
