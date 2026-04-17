
# Этап 6. Voice and Persona Layer  
## Обновлённый подробный план реализации voice и persona layer для fashion chatbot  
## С учётом `style_ingestion_semantic_distillation_plan_v2`, обновлённого Этапа 3 (Reasoning pipeline), обновлённого Этапа 4 (Profile Context) и обновлённого Этапа 5 (Knowledge Layer Expansion)

## 0. Назначение документа

Этот документ является **полноценной обновлённой версией Этапа 6** и заменяет прежнюю редакцию `6-voice_and_persona_layer_download.md` в рамках нового roadmap, где между Routing redesign и Reasoning pipeline уже добавлен отдельный этап `style_ingestion_semantic_distillation_plan_v2`.

Цель обновления:

- не строить voice layer как “ещё один prompt поверх текстового ответа”;
- встроить voice/persona architecture в уже обновлённую runtime-схему, где:
  - parser поставляет semantic-distilled style knowledge;
  - reasoning pipeline работает на richer style facets;
  - profile context выравнивает retrieved style bundles;
  - knowledge layer поставляет typed runtime knowledge;
- сделать так, чтобы voice layer **не придумывал fashion logic**, а формулировал уже полученный смысл;
- сохранить разделение knowledge / reasoning / voice / generation;
- сделать voice layer расширяемым под:
  - современного умного стилиста,
  - историка моды,
  - поэтику цвета и формы,
  - будущие tone experiments и A/B tests,
  - future editorial persona packs.

После parser upgrade и обновлённых Этапов 3–5 persona layer больше не может быть трактован как “красивый финальный prompt”. Он должен стать **отдельным presentation/composition слоем**, который работает поверх already structured meaning.

---

# 1. Контекст и причина обновления

## 1.1. Что изменилось в общей архитектуре

Изначальный Этап 6 уже правильно фиксировал важные принципы:
- bot should not “fully speak like Malevich” all the time;
- persona должна быть трёхслойной;
- knowledge layer и voice layer нельзя смешивать;
- visual prompt layer не должен получать художественное prose вместо структуры.

Эти принципы остаются верными.

Но после:
- `style_ingestion_semantic_distillation_plan_v2`,
- обновлённого reasoning pipeline,
- profile context v2,
- knowledge layer v2,

voice layer должен быть встроен **гораздо точнее**.

Теперь voice layer работает уже не поверх бедного coarse ответа, а поверх:
- `FashionReasoningOutput`;
- style logic points;
- visual language points;
- historical note candidates;
- styling rule candidates;
- CTA candidates;
- profile-aware reasoning result.

Следовательно, voice layer нужно переписать так, чтобы он:
- не подменял reasoning;
- не придумывал новые факты;
- не ломал `FashionBrief`;
- но при этом реально собирал узнаваемый и стабильный product voice.

---

## 1.2. Почему старая редакция Этапа 6 уже недостаточна

Старая редакция Этапа 6 была сильной концептуально, но теперь ей не хватает детализации в четырёх критичных местах:

1. Как именно `VoiceLayerComposer` должен использовать richer structured reasoning output.
2. Как persona layers должны активироваться в зависимости от mode / response type / context depth.
3. Как voice layer должен взаимодействовать с knowledge layer и profile-aware reasoning, не смешивая обязанности.
4. Как voice layer должен влиять на CTA, brevity, density and elegance of phrasing without mutating the underlying fashion logic.

Без этих уточнений voice layer рискует либо:
- снова стать “литературным шумом”,
- либо остаться thin wrapper without real architecture value.

---

# 2. Цель этапа

После реализации обновлённого Этапа 6 система должна:

1. Говорить как единый продуктовый персонаж, а не как набор случайных тональностей.
2. Всегда сохранять приоритет usefulness over theatricality.
3. Уметь комбинировать три слоя:
   - современный умный стилист;
   - историк моды;
   - поэтика цвета, света, ритма и формы.
4. Делать это контекстно, а не одинаково во всех ответах.
5. Работать поверх `FashionReasoningOutput`, а не напрямую поверх parser или DB.
6. Не тащить prose-style в visual prompt layer.
7. Формулировать CTA мягко и уместно.
8. Поддерживать разные уровни глубины ответа.
9. Оставаться расширяемым, тестируемым и управляемым на больших проектах.

---

# 3. Главный архитектурный принцип этапа

## 3.1. Voice layer не генерирует смысл — он формулирует его

Это центральное правило нужно зафиксировать жёстко:

> **Reasoning decides WHAT to say. Voice decides HOW to say it.**

### Reasoning отвечает за:
- fashion-domain логику;
- stylistic selection;
- interpretation of request;
- profile alignment effects;
- `FashionBrief`;
- CTA eligibility;
- clarification need;
- style logic and image logic.

### Voice отвечает за:
- тон;
- глубину;
- степень выразительности;
- ритм текста;
- уровень исторического контекста;
- уровень color/form poetics;
- human-readable phrasing;
- consistency of product personality.

---

## 3.2. Почему это критично

Если knowledge / reasoning / voice смешать:
- voice начнёт придумывать logic;
- reasoner станет слишком prose-heavy;
- prompt builder начнёт получать литературный шум;
- voice tests будут неотделимы от fashion tests;
- любые изменения в tone будут ломать смысловые контракты.

---

## 3.3. Voice layer также не должен подменять generation
Voice layer **не должен**:
- менять garments;
- менять palette;
- менять silhouette;
- менять `FashionBrief`;
- решать, что именно отправить в Comfy;
- генерировать raw prompt atoms.

Он может только:
- красиво объяснить уже выбранное;
- мягко предложить визуализацию;
- удержать единый product tone.

---

# 4. Обновлённая роль voice layer в runtime pipeline

## 4.1. Полная схема

```text
RoutingDecision
→ Retrieval + parser-distilled knowledge
→ Profile alignment
→ FashionReasoner
→ FashionReasoningOutput
→ VoiceLayerComposer
→ FinalResponse
→ optional CTA / generation handoff
```

---

## 4.2. Что это означает practically

Voice layer находится:
- **после reasoning**
- **до final response serialization**
- и **вне generation prompt construction**

Это важно, потому что:
- user-facing message и generation-facing brief должны быть разведены;
- бот может говорить богато, но generation должна получать structure, а не prose.

---

# 5. Новая целевая persona-модель

## 5.1. Persona не должна быть моно-ролью

Бот не должен стать:
- “полностью Малевичем”,
- “чистым историком моды”,
- “только сухим стилистом”.

Правильная модель остаётся трёхслойной, но теперь она должна быть formalized как runtime composition system.

---

## 5.2. Три слоя persona

### Слой 1. Базовый голос  
**Современный умный стилист**

Это дефолтный voice layer.

Он должен быть:
- спокойным;
- ясным;
- уверенным;
- не манерным;
- полезным;
- не сухим;
- дружелюбным, но не инфантильным.

Именно этот слой должен быть активен почти всегда.

---

### Слой 2. Историк моды  
Подключается контекстно.

Он добавляет:
- происхождение стилистики;
- культурную логику;
- связь с эпохой;
- объяснение, почему silhouette или комбинация вещей читается именно так;
- articulation of historical references, если reasoning их вернул.

Но он не должен:
- превращать каждый ответ в лекцию;
- перегружать обычный chat-heavy mode;
- спорить с practical styling outcome.

---

### Слой 3. Поэтика цвета и формы  
Это не literal “Малевич voice”, а controlled layer of:
- плоскости;
- света;
- ритма;
- контраста;
- тишины цвета;
- напряжения формы;
- отношения объёма и пустоты.

Он подключается:
- когда reasoning уже содержит `visual_language_points`;
- когда mode/response depth это допускает;
- когда это усиливает качество ответа, а не превращает его в литературный перформанс.

---

## 5.3. Итоговый продуктовый voice principle

Бот должен звучать как:

> умный современный стилист  
> с доступом к исторической глубине  
> и дисциплинированному языку цвета и формы

а не как:
- театральный персонаж;
- постоянный искусствоведческий монолог;
- экзальтированный поэт про одежду.

---

# 6. Что voice layer не должен делать

Voice layer не должен:
- выполнять routing;
- собирать retrieval;
- читать repositories;
- строить `FashionBrief`;
- пересобирать style logic;
- решать generation intent;
- переписывать негативные ограничения;
- менять profile-derived decisions;
- генерировать raw prompt for image model.

То есть voice — это **presentation composition layer**, а не “second reasoner” и не “final prompt magician”.

---

# 7. Новый компонент: `VoiceLayerComposer`

## 7.1. Назначение

Нужен отдельный application service:

```python
class VoiceLayerComposer(Protocol):
    async def compose(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
    ) -> StyledAnswer:
        ...
```

---

## 7.2. Почему он обязателен

Если voice оставить:
- внутри reasoner → reasoner станет God-object;
- внутри prompt template → не будет тестируемой архитектуры;
- во frontend → presentation logic окажется не там, где ей место.

Отдельный `VoiceLayerComposer`:
- соблюдает SRP;
- легко тестируется;
- позволяет эволюционно менять стиль;
- не смешивает смысл и подачу.

---

# 8. Новый `VoiceContext`

## 8.1. Почему нужен отдельный контекст

Voice layer не должен сам угадывать:
- насколько быть кратким;
- нужно ли углубляться;
- допустим ли исторический слой;
- допустим ли layer of color poetics;
- нужно ли делать CTA мягким или прямым.

Это должно приходить как явный runtime context.

---

## 8.2. Контракт

```python
class VoiceContext:
    mode: str
    response_type: str
    desired_depth: str
    should_be_brief: bool
    can_use_historical_layer: bool
    can_use_color_poetics: bool
    can_offer_visual_cta: bool
    profile_context_present: bool
    knowledge_density: str
```

---

## 8.3. Что означают поля

### `mode`
Current scenario:
- `general_advice`
- `style_exploration`
- `occasion_outfit`
- `garment_matching`
- `clarification_only`

### `response_type`
То, что вернул reasoning:
- `text_only`
- `clarification`
- `text_with_brief`
- `text_with_visual_offer`
- `brief_ready_for_generation`

### `desired_depth`
Насколько глубоким должен быть ответ:
- `light`
- `normal`
- `deep`

### `should_be_brief`
Нужно ли отвечать коротко.

### `can_use_historical_layer`
Можно ли подключать historian layer.

### `can_use_color_poetics`
Можно ли подключать color/form poetics.

### `can_offer_visual_cta`
Можно ли в этом ответе предлагать визуализацию.

### `knowledge_density`
Примерная плотность материала:
- `low`
- `medium`
- `high`

Это полезно, чтобы voice layer понимал, насколько богато можно формулировать ответ.

---

# 9. Новый `StyledAnswer`

## 9.1. Контракт результата

```python
class StyledAnswer:
    text: str
    tone_profile: str
    voice_layers_used: list[str]
    includes_historical_note: bool
    includes_color_poetics: bool
    cta_text: str | None
    brevity_level: str
```

---

## 9.2. Зачем нужен структурированный результат

Если voice layer вернёт только string:
- сложно тестировать;
- сложно логировать;
- сложно оценивать, какой слой реально был активирован;
- сложно делать A/B tests;
- сложно debugg’ить product tone regressions.

---

# 10. Входные данные voice layer после обновления Этапа 3

## 10.1. Что теперь получает voice layer

После обновлённого Reasoning pipeline voice layer должен получать richer structured output:

- `text_response`
- `clarification_question`
- `fashion_brief`
- `can_offer_visualization`
- `suggested_cta`
- `style_logic_points`
- `visual_language_points`
- `historical_note_candidates`
- `styling_rule_candidates`
- `image_cta_candidates`

---

## 10.2. Почему это важно

Теперь voice layer формулирует ответ:
- не “из пустоты”;
- не на основе parser tables;
- не на основе случайных text chunks;
- а на основе already normalized and structured meaning.

Это радикально повышает устойчивость product voice.

---

# 11. Уровни глубины ответа

## 11.1. Почему depth control обязателен

Если бот всегда будет:
- длинным,
- образным,
- “умным”,
- историческим,
- почти-литературным,

то продукт быстро станет:
- утомительным;
- неестественным;
- слишком тяжёлым для обычного диалога;
- нестабильным по UX.

---

## 11.2. Нужно ввести три режима глубины

### `light`
Используется:
- для простых бытовых запросов;
- для быстрых уточнений;
- для general advice;
- когда пользователь явно не просит deep dive.

### `normal`
Это основной рабочий режим.

Он должен:
- быть понятным;
- немного объяснять логику;
- не перегружать ответ.

### `deep`
Используется:
- когда есть сильный stylistic or historical angle;
- когда запрос rich and aesthetic-heavy;
- когда persona layers действительно усиливают ответ.

---

## 11.3. Что depth должен менять

Depth влияет на:
- длину ответа;
- количество объясняющих блоков;
- вероятность подключения historical layer;
- вероятность подключения color/form poetics;
- плотность stylistic explanation.

---

# 12. Адаптивность voice по сценариям

## 12.1. В `general_advice`
Нужно:
- коротко;
- ясно;
- полезно;
- без excess literary density.

Voice layers:
- базовый стилист = да
- историк = редко
- color/form poetics = редко

---

## 12.2. В `occasion_outfit`
Нужно:
- чуть более структурно;
- объяснять логику выбора;
- показывать баланс between occasion + wearability.

Voice layers:
- базовый стилист = всегда
- историк = иногда
- color/form = иногда

---

## 12.3. В `style_exploration`
Нужно:
- больше выразительности;
- можно чуть богаче язык;
- visual CTA может быть органичнее.

Voice layers:
- базовый стилист = всегда
- историк = часто уместен
- color/form = часто уместен

---

## 12.4. В `clarification`
Нужно:
- максимально просто;
- не артистично;
- без философии;
- без перегрузки.

Voice layers:
- только базовый стилист

---

# 13. Новый принцип voice adaptation

## 13.1. “Один бот, а не три разных”
Важно добиться эффекта:

> Это всегда один и тот же бот,  
> но с разной степенью глубины и выразительности в зависимости от контекста.

---

## 13.2. Как этого добиться
Через:
- единый базовый tone policy;
- controlled optional layers;
- contextual activation rules;
- ограничения на частоту/интенсивность expressive layers.

---

# 14. Исторический слой

## 14.1. Что именно делает historical layer
Он должен:
- связывать образ со стилевой или культурной логикой;
- объяснять происхождение визуального решения;
- добавлять интеллектуальную глубину;
- помогать читать стиль не как набор вещей, а как часть fashion context.

---

## 14.2. Что он не должен делать
Он не должен:
- захватывать весь ответ;
- спорить с практичностью;
- доминировать над stylist layer;
- включаться автоматически на каждое сообщение.

---

## 14.3. Источник данных
Historical layer должен опираться на:
- `historical_note_candidates` из reasoning;
- future `fashion_historian` provider;
- relation/context cards из knowledge layer.

То есть voice layer не генерирует history “из воздуха”, а формулирует уже retrieved and reasoned context.

---

# 15. Поэтика цвета и формы

## 15.1. Что это такое в новой архитектуре
Это не “говорить как Малевич”, а controlled lexicon of:
- plane / surface
- light
- rhythm
- contrast
- tension of form
- color quietness
- volume and spacing

---

## 15.2. Когда этот слой уместен
Когда:
- ответ связан с visual mood;
- reasoning already produced `visual_language_points`;
- image direction действительно важна;
- дополнительная поэтика усиливает понимание, а не отвлекает.

---

## 15.3. Когда он неуместен
Когда:
- пользователь просто спросил practical thing;
- clarification is needed;
- ответ должен быть очень кратким;
- underlying reasoning is weak or generic.

---

## 15.4. Источник данных
Этот слой должен опираться на:
- `visual_language_points`;
- future color-theory / Malevich provider cards;
- style visual language knowledge cards.

---

# 16. CTA composition

## 16.1. Voice layer не решает, можно ли давать CTA
Это решает reasoning/policy.

Но voice layer решает:
- как её сформулировать;
- насколько мягко;
- насколько естественно вшить её в ответ.

---

## 16.2. Примеры CTA styles

### Более нейтральный:
- “Могу собрать для этого flat lay референс.”

### Более мягкий:
- “Если хочешь, могу показать это как flat lay.”

### Более editorial:
- “Если полезно, можно собрать визуальный референс, чтобы увидеть, как эта логика работает в образе.”

---

## 16.3. Что влияет на выбор формулировки
- response depth
- mode
- confidence of image facet bundle
- user’s recent interaction style
- whether user already hinted visual intent

---

# 17. Голос и profile context

## 17.1. Voice layer не применяет profile, но должен знать, что profile already influenced reasoning
Это важно, чтобы:
- не задавать лишние вопросы;
- не звучать так, будто ответ “общий”;
- подчеркивать персонализированность мягко, без навязчивости.

---

## 17.2. Что это означает practically
Voice layer может формулировать:
- “Для тебя здесь лучше работает более собранный силуэт…”
- “Я бы удержал образ в более мягкой подаче…”
- “Я бы не уводил это в слишком жёсткую геометрию…”

Но только если reasoning уже это решил.

---

# 18. Голос и generation

## 18.1. Строгое разделение
Voice layer может:
- описать visual idea;
- предложить visual CTA;
- помочь пользователю понять, почему visual branch уместна.

Но voice layer не должен:
- создавать raw image prompt;
- влиять на prompt atoms;
- менять generation constraints;
- добавлять literary noise в visual pipeline.

---

## 18.2. Почему это критично
Именно это защищает generation layer от:
- prose pollution;
- tone drift;
- inconsistent prompt construction.

---

# 19. Новые application-level сервисы

## 19.1. `VoiceLayerComposer`
Главный сервис.

## 19.2. `VoiceTonePolicy`
Отдельный policy service, который определяет:
- какие voice layers доступны;
- какие запрещены в текущем context;
- какой depth mode нужен.

```python
class VoiceTonePolicy(Protocol):
    async def resolve(self, context: VoiceContext) -> VoiceToneDecision:
        ...
```

---

## 19.3. `VoiceStyleGuideRepository`
Полезен для хранения:
- reusable tone rules;
- stylist layer rules;
- historian layer rules;
- color/form poetics lexicon;
- CTA style guide.

Это помогает:
- не хардкодить всё в одном giant prompt;
- versionировать voice policies;
- делать A/B testing later.

---

## 19.4. `VoicePromptBuilder`
Если voice still backed by LLM prompt, лучше выделить отдельный builder:

```python
class VoicePromptBuilder(Protocol):
    async def build(
        self,
        reasoning_output: FashionReasoningOutput,
        context: VoiceContext,
        tone_decision: VoiceToneDecision,
    ) -> VoicePrompt:
        ...
```

---

# 20. Почему нужен `VoiceTonePolicy`

## 20.1. Если всё оставить внутри composer
Тогда:
- activation rules размажутся;
- появится огромный God-composer;
- сложно будет объяснить, почему включился historian / Malevich layer;
- сложно будет тестировать consistency.

---

## 20.2. Что решает `VoiceTonePolicy`
Он определяет:
- allowed layers;
- brevity requirements;
- maximum expressive density;
- CTA softness;
- whether to include historical note;
- whether to include color/form phrasing.

---

# 21. Возможная модель `VoiceToneDecision`

```python
class VoiceToneDecision:
    base_tone: str
    use_historian_layer: bool
    use_color_poetics_layer: bool
    brevity_level: str
    expressive_density: str
    cta_style: str | None
```

---

# 22. Голос как конфигурируемый слой

## 22.1. Почему это важно
На больших проектах voice обычно:
- меняется;
- тестируется;
- A/B-шится;
- адаптируется под сегменты или продукты.

Поэтому voice layer нельзя захардкодить как один статичный текстовый трюк.

---

## 22.2. Что должно быть конфигурируемым
- tone policies
- layer activation rules
- CTA style
- max depth
- max historical density
- max color-poetics density
- per-mode defaults

---

# 23. Admin flags и feature flags

## 23.1. Что нужно уметь включать/выключать
- `voice.historian.enabled`
- `voice.color_poetics.enabled`
- `voice.deep_mode.enabled`
- `voice.cta.experimental_copy.enabled`

---

## 23.2. Где это применяется
- `VoiceTonePolicy`
- `VoiceLayerComposer`
- `VoicePromptBuilder`

---

# 24. Наблюдаемость

## 24.1. Что логировать
Для каждого ответа:
- mode
- response_type
- desired_depth
- voice layers used
- historical layer used / skipped
- color poetics used / skipped
- CTA used / skipped
- brevity level
- output length

---

## 24.2. Почему это важно
Без этого нельзя понять:
- почему ответы стали тяжелее или суше;
- где voice layer перегружает продукт;
- где CTA звучит неуместно;
- почему пользователи воспринимают ответы как “слишком литературные”.

---

# 25. Тестирование

## 25.1. Unit tests
Нужны на:
- `VoiceTonePolicy`
- `VoicePromptBuilder`
- `VoiceLayerComposer`
- CTA style selection

---

## 25.2. Integration tests
Нужны сценарии:
- light general advice
- occasion outfit normal depth
- deep style exploration
- clarification only
- strong visual-language answer
- no-history answer even if history provider available

---

## 25.3. Product tests
Нужно проверять:
- bot feels intelligent, not theatrical
- text remains useful
- persona remains consistent
- responses do not become too long
- CTA feels natural

---

# 26. Clean Architecture / SOLID

## 26.1. Domain layer
- `VoiceContext`
- `StyledAnswer`
- `VoiceToneDecision`

## 26.2. Application layer
- `VoiceLayerComposer`
- `VoiceTonePolicy`
- `VoicePromptBuilder`

## 26.3. Infrastructure layer
- style guide repository
- prompt templates
- feature flag adapters
- metrics/logging

## 26.4. Interface layer
- final response mappers
- chat DTOs
- CTA rendering DTOs

---

## 26.5. SOLID акценты

### SRP
- reasoning = смысл
- voice tone policy = выбор стиля подачи
- composer = сборка ответа
- CTA phrasing = отдельная policy concern

### OCP
Новые persona layers и новые tone styles должны добавляться расширением, а не переписыванием ядра.

### DIP
Voice layer зависит от `FashionReasoningOutput` и voice contracts, а не от parser tables, DB или raw source texts.

---

# 27. Пошаговый план реализации

## Подэтап 1. Обновить contracts
- `VoiceContext`
- `StyledAnswer`
- `VoiceToneDecision`

## Подэтап 2. Реализовать `VoiceTonePolicy`
- layer activation rules
- brevity policy
- expressive density policy
- CTA style policy

## Подэтап 3. Реализовать `VoicePromptBuilder`
- structured input → voice prompt
- layer-aware prompt shaping

## Подэтап 4. Реализовать `VoiceLayerComposer`
- reasoning output → styled answer
- CTA phrasing
- final text shaping

## Подэтап 5. Подключить feature flags
- historian layer
- color poetics layer
- deep mode toggles

## Подэтап 6. Интегрировать в runtime
- reasoner → voice composer → final response
- no direct coupling to parser or generation

## Подэтап 7. Добавить observability и tests
- logs
- metrics
- unit tests
- integration tests
- product tone tests

---

# 28. Acceptance criteria

Этап считается завершённым, если:

1. Voice layer отделён от reasoning.
2. Voice layer не придумывает new fashion logic.
3. `VoiceLayerComposer` работает на `FashionReasoningOutput`.
4. Есть отдельный `VoiceTonePolicy`.
5. Поддерживаются три слоя persona:
   - stylist
   - historian
   - color/form poetics
6. Их активация зависит от context, а не работает одинаково всегда.
7. CTA формулируется через отдельную controlled policy.
8. Voice layer не влияет на `FashionBrief` и generation constraints.
9. Есть feature flags и observability.
10. Ответы остаются полезными, читаемыми и consistent.

---

# 29. Definition of Done

Этап реализован корректно, если:
- бот звучит как единый продуктовый персонаж;
- ответы ощущаются умными, но не тяжёлыми;
- historical и color/form layers подключаются уместно;
- нет потери смысла между reasoning и final response;
- generation layer не загрязняется prose;
- дальнейшее расширение persona layer возможно без переписывания core runtime.

---

# 30. Архитектурный итог этапа

После реализации обновлённого Этапа 6 система получает не “красивый финальный prompt”, а полноценный **voice composition layer**, который:

- работает поверх structured reasoning;
- уважает profile-aware и knowledge-backed смысл;
- делает продукт узнаваемым;
- не ломает generation architecture;
- не смешивает knowledge, reasoning и presentation;
- оставляет пространство для эволюции tone system на большом масштабируемом проекте.

Именно это превращает voice/persona layer из stylistic garnish в **реальный архитектурный слой продукта**, который делает fashion reasoning assistant не просто полезным, но и целостным по голосу.
