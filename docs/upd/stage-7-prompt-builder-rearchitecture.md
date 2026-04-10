
# Этап 7. Полностью перестроить prompt builder

## Контекст этапа

В архитектурном плане проекта Этап 7 сформулирован как полная перестройка prompt builder. В самом плане зафиксировано, что текущий длинный описательный prompt должен быть заменён на **структурированный fashion brief**, а prompt builder — разделён на два независимых слоя:
1. **Fashion reasoning**
2. **Image prompt compiler**

План также прямо фиксирует обязательные поля нового промежуточного объекта:
- `style_identity`
- `historical_reference`
- `tailoring_logic`
- `color_logic`
- `garment_list`
- `palette`
- `materials`
- `styling_notes`
- `composition_rules`
- `negative_constraints`
- `diversity_constraints` citeturn409760view0

Именно этот этап должен перестать полагаться на “один большой текст”, который смешивает reasoning, styling, history, anti-repeat и image prompt в один хрупкий output.

Этот этап опирается на:
- **Этап 0** — ingestion pipeline и knowledge base;
- **Этап 1** — доменную модель и state machine;
- **Этап 3** — explicit orchestrator;
- **Этап 4** — полноценный `garment_matching`;
- **Этап 5** — slot-filling `occasion_outfit`;
- **Этап 6** — persistent `style_history` и `diversity_constraints`.

---

# 1. Цель этапа

Перестроить prompt builder так, чтобы система:

- не строила generation prompt как “длинный магический текст”;
- сначала формировала **структурированный fashion brief**;
- затем компилировала его в стабильный и проверяемый generation payload;
- отделяла reasoning о стиле от image generation instructions;
- могла валидировать, тестировать и логировать каждую стадию отдельно;
- поддерживала разные режимы (`general_advice`, `garment_matching`, `style_exploration`, `occasion_outfit`) без копирования хаотичных prompt templates;
- была готова к смене модели, знаниям из базы и дальнейшему росту.

---

# 2. Архитектурная проблема текущего prompt builder

Симптомы текущего состояния хорошо предсказуемы:
1. слишком общий и монолитный prompt;
2. reasoning и generation instructions смешаны в одном тексте;
3. контекст частично теряется между decision layer и image backend;
4. prompt трудно тестировать;
5. semantic diversity и visual diversity либо не доходят до финального prompt, либо растворяются в тексте;
6. knowledge layer трудно подмешивать структурированно;
7. невозможно объяснимо контролировать, почему generated image получилась именно такой.

В архитектурном плане это прямо обозначено как необходимость уйти от одного длинного описательного prompt и перейти к промежуточному structured brief. citeturn409760view0

---

# 3. Архитектурные принципы реализации

## 3.1. Clean Architecture

### Domain layer
Содержит:
- `FashionBrief`
- `StyleIdentity`
- `ColorLogic`
- `TailoringLogic`
- `CompositionRules`
- `NegativeConstraints`
- `DiversityConstraints`
- value objects для palette, garments, materials и visual presets

### Application layer
Содержит:
- `FashionReasoningService`
- `FashionBriefBuilder`
- `ImagePromptCompiler`
- `PromptValidationUseCase`
- `GenerationPayloadBuilder`
- orchestration bindings между scenario handlers и prompt pipeline

### Infrastructure layer
Содержит:
- LLM adapters;
- knowledge retrieval adapters;
- template repositories;
- Comfy workflow payload adapters;
- prompt persistence/logging adapters.

### Interface layer
Содержит:
- DTO serializers;
- admin/debug prompt inspection endpoints;
- optional preview endpoint для compiled prompt.

## 3.2. SOLID

### Single Responsibility
- reasoning service думает о стиле;
- brief builder собирает domain object;
- compiler превращает brief в image prompt;
- payload builder переводит compiled prompt в формат конкретного image backend;
- validator проверяет completeness/consistency.

### Open/Closed
Новые режимы, стили, visual presets и knowledge packs добавляются без переписывания всей цепочки.

### Liskov
Все компиляторы image prompts должны быть взаимозаменяемы:
- `ComfyImagePromptCompiler`
- `MockImagePromptCompiler`
- позже возможен другой backend

### Interface Segregation
Нужны отдельные интерфейсы:
- `FashionReasoner`
- `FashionBriefRepository`
- `PromptCompiler`
- `PromptValidator`
- `GenerationPayloadAdapter`

### Dependency Inversion
Application layer зависит от абстракций, а не от конкретного vLLM/Comfy implementation.

## 3.3. FSD / модульная декомпозиция

Рекомендуемая backend-структура:

```text
apps/backend/app/
  domain/
    prompt_building/
      entities/
      value_objects/
      policies/
      enums/
  application/
    prompt_building/
      services/
        fashion_reasoning_service.py
        fashion_brief_builder.py
        image_prompt_compiler.py
        prompt_validator.py
        generation_payload_builder.py
      use_cases/
        build_fashion_brief.py
        compile_image_prompt.py
        validate_prompt_pipeline.py
  infrastructure/
    llm/
    knowledge/
    prompt_templates/
    comfy/
    persistence/
  interfaces/
    api/
      routes/
      serializers/
```

---

# 4. Главная архитектурная идея этапа

Промпт больше не является “главным носителем смысла”.  
Главным носителем смысла становится **FashionBrief**.

Цепочка должна выглядеть так:

```text
Scenario context
→ Knowledge retrieval
→ Fashion reasoning
→ Structured FashionBrief
→ Validation
→ Image prompt compiler
→ Generation payload
→ ComfyUI
```

Это и есть принципиальная перестройка, требуемая в плане. citeturn409760view0

---

# 5. Новый центральный доменный объект: FashionBrief

## 5.1. Что это такое
`FashionBrief` — это промежуточная структурированная модель, которая:
- описывает стиль и образ на языке предметной области;
- не зависит от конкретного backend генерации;
- может быть проверена, сохранена, логирована и скомпилирована в разные форматы.

## 5.2. Обязательные поля
На основе плана:

```python
class FashionBrief(BaseModel):
    style_identity: str
    historical_reference: list[str] = []
    tailoring_logic: list[str] = []
    color_logic: list[str] = []
    garment_list: list[str] = []
    palette: list[str] = []
    materials: list[str] = []
    styling_notes: list[str] = []
    composition_rules: list[str] = []
    negative_constraints: list[str] = []
    diversity_constraints: dict = Field(default_factory=dict)
```

Это минимальный обязательный слой. Дополнительно стоит ввести:

```python
class FashionBrief(BaseModel):
    style_identity: str
    style_family: str | None = None
    brief_mode: str
    occasion_context: dict | None = None
    anchor_garment: dict | None = None
    historical_reference: list[str] = []
    tailoring_logic: list[str] = []
    color_logic: list[str] = []
    garment_list: list[str] = []
    palette: list[str] = []
    materials: list[str] = []
    footwear: list[str] = []
    accessories: list[str] = []
    styling_notes: list[str] = []
    composition_rules: list[str] = []
    negative_constraints: list[str] = []
    diversity_constraints: dict = Field(default_factory=dict)
    visual_preset: str | None = None
    generation_intent: str | None = None
```

## 5.3. Почему это важно
Без `FashionBrief` система не может:
- валидировать смысл до генерации;
- отделить reasoning от image instructions;
- подключать knowledge layer в управляемом виде;
- тестировать prompt pipeline по частям;
- объяснять и логировать логику подбора.

---

# 6. Двухслойная архитектура prompt builder

## 6.1. Слой 1 — Fashion reasoning

План прямо говорит, что LLM должна сначала думать как:
- историк моды;
- портной;
- стилист по цвету и силуэту. citeturn409760view0

### Роль слоя
Fashion reasoning:
- принимает сценарный контекст;
- достаёт knowledge;
- решает, какие вещи, формы, материалы, цвета и references уместны;
- формирует **FashionBrief**.

### Что не делает этот слой
- не пишет final prompt для Comfy;
- не знает деталей workflow JSON;
- не думает в терминах sampler / negative prompt weights;
- не зависит от image backend.

## 6.2. Слой 2 — Image prompt compiler

План прямо требует отдельный builder, который переводит structured brief в безопасный и стабильный prompt для ComfyUI. citeturn409760view0

### Роль слоя
Compiler:
- получает `FashionBrief`;
- превращает его в:
  - final prompt
  - negative prompt
  - visual preset
  - generation metadata
  - workflow payload bindings

### Что не делает этот слой
- не принимает fashion-решения;
- не выбирает стиль сам;
- не оценивает полноту occasion slots;
- не определяет anti-repeat по памяти самостоятельно.

---

# 7. Fashion reasoning layer

## 7.1. Входные данные

`FashionReasoningInput` должен собираться orchestrator/handler-ом и включать:

```python
class FashionReasoningInput(BaseModel):
    mode: str
    user_message: str | None = None
    anchor_garment: dict | None = None
    occasion_context: dict | None = None
    style_direction: dict | None = None
    style_history: list[dict] = []
    diversity_constraints: dict = Field(default_factory=dict)
    knowledge_cards: list[dict] = []
    profile_context: dict | None = None
    visual_preset_candidates: list[str] = []
```

## 7.2. Источники знания
Fashion reasoning должен работать не только от LLM memory, а от retrieval + domain context:

- style catalog
- style traits
- fashion history
- color theory
- tailoring principles
- materials/fabrics
- flatlay prompt patterns

Это соответствует Этапу 8 общего плана, но hook для knowledge должен быть встроен уже сейчас. citeturn409760view0

## 7.3. Выход
Результат reasoning — это не текст.  
Результат reasoning — это **FashionBrief**.

---

# 8. Image prompt compiler

## 8.1. Центральная задача
Компилятор превращает `FashionBrief` в generation representation, пригодное для image backend.

Рекомендуемая модель:

```python
class CompiledImagePrompt(BaseModel):
    final_prompt: str
    negative_prompt: str
    visual_preset: str | None = None
    palette_tags: list[str] = []
    garment_tags: list[str] = []
    style_tags: list[str] = []
    composition_tags: list[str] = []
    metadata: dict = Field(default_factory=dict)
```

## 8.2. Почему нельзя компилировать prompt прямо в handler
Иначе:
- логика режимов смешается с image backend деталями;
- любой change в prompt syntax потребует переписывать scenario handlers;
- невозможно будет делать независимые тесты и валидаторы.

## 8.3. Compiler-specific responsibility
Compiler должен:
- переводить palette в визуальные теги;
- переводить garments и materials в image-safe vocabulary;
- собирать composition hints;
- прокладывать negative constraints;
- подмешивать diversity constraints;
- учитывать mode-specific visual preset.

---

# 9. Prompt validation layer

## 9.1. Зачем нужен validator
Если `FashionBrief` или compiled prompt неполны, неконсистентны или конфликтуют сами с собой, это нужно ловить **до generation job**, а не после странной картинки.

## 9.2. Что валидировать

### На уровне FashionBrief
- есть ли `style_identity`;
- не пуст ли `garment_list`;
- не конфликтуют ли palette и negative constraints;
- не отсутствует ли tailoring/color logic в режимах, где она обязательна;
- доходят ли diversity constraints.

### На уровне CompiledImagePrompt
- prompt не пустой;
- negative prompt не пустой, если должен быть;
- присутствуют mode-relevant tags;
- выбран visual preset;
- есть metadata для observability.

## 9.3. Контракт

```python
class PromptValidator(Protocol):
    async def validate_brief(self, brief: FashionBrief) -> list[str]: ...
    async def validate_compiled(self, prompt: CompiledImagePrompt) -> list[str]: ...
```

---

# 10. Mode-specific prompt pipelines

План прямо говорит, что у каждого режима должен быть **свой prompt-building pipeline**. citeturn409760view0

## 10.1. `general_advice`
Обычно generation не обязательна, но если generation всё же нужна:
- brief легче;
- emphasis на stylistic explanation;
- меньше composition constraints.

## 10.2. `garment_matching`
Prompt pipeline должен:
- делать `anchor_garment` центральным;
- вокруг него строить outfit logic;
- усиливать compatibility, silhouette balance и color harmony;
- держать `anchor garment centrality high`.

## 10.3. `style_exploration`
Pipeline должен:
- учитывать `style_history`;
- передавать `diversity_constraints`;
- делать anti-repeat обязательной частью brief;
- разрешать больший уровень visual experimentation.

## 10.4. `occasion_outfit`
Pipeline должен:
- опираться на `occasion_context`;
- сохранять event suitability;
- учитывать dress code / desired impression;
- prioritise practical coherence.

---

# 11. Prompt template system

## 11.1. Почему templates нужны
Даже если reasoning даёт structured brief, compiler должен использовать управляемую систему шаблонов, а не случайный string concatenation.

## 11.2. Что должно быть шаблонизировано
- base prompt skeleton для каждого режима;
- negative prompt skeleton;
- visual preset mappings;
- composition phrase mappings;
- palette language mappings;
- material-to-visual-token mappings.

## 11.3. Где должны жить templates
В infrastructure layer, например:

```text
infrastructure/prompt_templates/
  general_advice/
  garment_matching/
  style_exploration/
  occasion_outfit/
```

Или как typed registries в Python modules.

---

# 12. Связь с knowledge layer

## 12.1. Prompt builder не должен “вспоминать знания сам”
Он должен получать уже отобранные knowledge cards и использовать их структурно.

## 12.2. Примеры knowledge injection
- `historical_reference` ← fashion history cards
- `color_logic` ← color theory cards
- `tailoring_logic` ← tailoring principles
- `materials` ← materials/fabrics cards
- `style_identity` / `garment_list` ← style catalog / style traits

## 12.3. Архитектурное правило
Knowledge retrieval должен происходить **до** fashion reasoning или во время reasoning input assembly, но не быть зашитым прямо в compiler.

---

# 13. Diversity constraints в новом prompt builder

## 13.1. Обязательное требование
Согласно Этапу 6, anti-repeat должен дойти до final generation prompt и Comfy input. Новый prompt builder — именно то место, где это должно быть гарантировано. citeturn409760view0

## 13.2. Что должен делать compiler
Он должен:
- прокладывать `avoid previous palette`;
- включать semantic exclusions;
- включать visual exclusions;
- выбирать альтернативный visual preset;
- компилировать negative constraints в safe image language.

## 13.3. Что нельзя делать
Нельзя хранить diversity constraints только как “примечание” без фактического использования в compiled prompt.

---

# 14. Generation payload builder

## 14.1. Последний слой перед image backend
После компиляции нужен отдельный builder, который адаптирует compiled prompt под конкретный backend.

Например:

```python
class GenerationPayload(BaseModel):
    workflow_name: str
    prompt: str
    negative_prompt: str
    visual_preset: str | None = None
    metadata: dict = Field(default_factory=dict)
```

## 14.2. Почему это отдельный слой
Потому что:
- ComfyUI payload ≠ universal prompt object;
- завтра backend может измениться;
- детали workflow не должны протекать обратно в domain/application.

## 14.3. Важное правило
`FashionBrief` и `CompiledImagePrompt` не должны зависеть от конкретного Comfy workflow JSON.

---

# 15. Что должен делать новый prompt pipeline в каждом сценарии

## 15.1. Для `garment_matching`
- anchor garment становится обязательной доменной частью brief;
- compiler подчёркивает центральность вещи;
- negative constraints запрещают style drift;
- composition rules подчеркивают outfit around anchor item.

## 15.2. Для `occasion_outfit`
- brief включает occasion suitability;
- compiler учитывает dress code / desired impression;
- negative constraints предотвращают неуместные сочетания.

## 15.3. Для `style_exploration`
- brief включает style history;
- compiler обеспечивает anti-repeat;
- visual preset deliberately shifts.

---

# 16. Роль orchestrator относительно prompt builder

Новый orchestrator из Этапа 3 не должен собирать final prompt сам. Его работа:
1. определить режим;
2. собрать контекст;
3. запросить reasoning;
4. получить `FashionBrief`;
5. прогнать validation;
6. вызвать compiler;
7. построить generation payload;
8. создать generation job.

То есть prompt builder становится отдельной вертикалью, а не “частью if-ветки” оркестратора.

---

# 17. Frontend и prompt pipeline

Frontend не должен знать ничего о том:
- как строится brief;
- как компилируется prompt;
- как выбирается visual preset.

Но для отладки и удобства поддержки полезно предусмотреть:
- admin/debug endpoint preview compiled brief;
- admin/debug endpoint preview compiled prompt;
- traces по `prompt_hash` и `brief_hash`.

Это даст прозрачность без утечки внутренней логики в UI.

---

# 18. Observability

## 18.1. Что логировать
На каждый prompt pipeline run:
- `session_id`
- `message_id`
- `mode`
- `brief_hash`
- `compiled_prompt_hash`
- `style_id`
- `visual_preset`
- `diversity_constraints_hash`
- `knowledge_cards_count`
- `validation_errors_count`
- `generation_job_id`

## 18.2. Что сохранять
Для каждой генерации:
- `FashionBrief`
- compiled prompt
- negative prompt
- chosen visual preset
- style metadata
- palette tags
- garments tags
- diversity constraints
- workflow name / version

Это полностью согласуется с требованием плана сохранять метаданные генерации и делает систему анализируемой. citeturn409760view0

---

# 19. Тестирование

## 19.1. Unit tests
Покрыть:
- `FashionBriefBuilder`
- `ImagePromptCompiler`
- `PromptValidator`
- mode-specific template resolution
- diversity propagation
- payload adapter

## 19.2. Integration tests
Покрыть:
- reasoning input -> FashionBrief
- FashionBrief -> compiled prompt
- compiled prompt -> generation payload
- anti-repeat survives full pipeline
- occasion / garment / style-specific branches

## 19.3. E2E сценарии
Минимальный набор:
1. `garment_matching` builds anchor-centered brief and compiled prompt
2. `occasion_outfit` carries slot logic into final prompt
3. `style_exploration` propagates history and diversity constraints
4. prompt validation catches incomplete briefs
5. generation payload contains all required metadata

---

# 20. Рекомендуемая модульная структура

```text
domain/prompt_building/
  entities/
    fashion_brief.py
    compiled_image_prompt.py
    generation_payload.py
  value_objects/
    style_identity.py
    color_logic.py
    tailoring_logic.py
    composition_rules.py
    negative_constraints.py
    diversity_constraints.py

application/prompt_building/
  services/
    fashion_reasoning_service.py
    fashion_brief_builder.py
    image_prompt_compiler.py
    prompt_validator.py
    generation_payload_builder.py
  use_cases/
    build_fashion_brief.py
    compile_image_prompt.py
    validate_compiled_prompt.py

infrastructure/prompt_templates/
  garment_matching/
  style_exploration/
  occasion_outfit/
  common/

infrastructure/comfy/
  comfy_generation_payload_adapter.py
```

---

# 21. Что не надо делать на этом этапе

Чтобы не разрушить архитектуру, нельзя:
- продолжать строить prompt как один giant string в handler;
- мешать reasoning и image instructions в одном output;
- считать LLM output сразу final prompt без intermediate brief;
- держать mode-specific prompt logic в route/orchestrator;
- терять diversity constraints между reasoning и compiled prompt;
- вшивать Comfy workflow details в domain objects;
- решать неполноту brief уже после enqueue job.

---

# 22. Пошаговый план реализации Этапа 7

## Подэтап 7.1. Ввести `FashionBrief`
Создать центральный domain object и сериализацию.

## Подэтап 7.2. Реализовать `FashionReasoningService`
Сервис, который строит structured brief из сценарного контекста и knowledge.

## Подэтап 7.3. Реализовать `ImagePromptCompiler`
Отдельный compiler для compiled image prompt.

## Подэтап 7.4. Реализовать `PromptValidator`
Проверка completeness / consistency до generation.

## Подэтап 7.5. Реализовать `GenerationPayloadBuilder`
Адаптация под Comfy payload без утечки backend details в domain.

## Подэтап 7.6. Вынести mode-specific templates
Сделать управляемую систему шаблонов по режимам.

## Подэтап 7.7. Протянуть diversity и knowledge до финального payload
Проверить, что nothing is lost in the pipeline.

## Подэтап 7.8. Добавить observability и тесты
Сделать prompt pipeline измеримым и поддерживаемым.

---

# 23. Критерии готовности этапа

Этап 7 реализован корректно, если:

1. Prompt builder больше не строит generation prompt как один длинный ad hoc текст.
2. В системе есть центральный `FashionBrief`.
3. Prompt pipeline разделён на `Fashion reasoning` и `Image prompt compiler`.
4. `FashionBrief` валидируется до генерации.
5. Knowledge cards доходят до brief структурированно.
6. Diversity constraints доходят до final generation payload.
7. `garment_matching`, `style_exploration`, `occasion_outfit` используют разные mode-specific prompt pipelines.
8. Comfy workflow детали изолированы в payload adapter.
9. Prompt pipeline покрыт unit / integration / e2e тестами.
10. Система сохраняет достаточные метаданные для анализа качества.

---

# 24. Архитектурный итог этапа

После реализации Этапа 7 prompt builder перестаёт быть хрупким местом, где теряется смысл, и становится полноценным многошаговым pipeline:

- с отдельным fashion reasoning;
- с центральным structured brief;
- с независимым image compiler;
- с валидируемостью;
- с knowledge-driven logic;
- с корректной прокладкой diversity constraints;
- с mode-specific composition;
- с хорошей поддерживаемостью и наблюдаемостью.

Именно после такого изменения проект перестаёт зависеть от качества “одной удачной prompt-строки” и начинает вести себя как зрелая, масштабируемая fashion reasoning system.
