
# Полный план redesign главной страницы, chat UI и admin audit-слоя  
## На основе распакованных исходников `portfolio-main-3.zip`  
## Для Cursor / implementation use  
## С учётом OOP, SOLID, FSD, чистоты кода, поддерживаемости и масштабируемости

## 0. Назначение документа

Этот документ описывает **полный план переработки frontend и части backend/admin**, чтобы:

1. изменить дизайн **всей главной страницы**, а не только chat-блока;
2. вывести визуальное качество интерфейса на уровень ощущения, близкий к референсу Adobe Podcast Enhance:
   - мягкие большие поверхности,
   - крупные скругления,
   - воздух,
   - ясная иерархия,
   - спокойный premium UI;
3. при этом сохранить и встроить уже зафиксированное поведение:
   - круговой **60-секундный loader/countdown вместо send button**;
   - блокировку чата после отправки;
   - блокировку после `Попробовать другой стиль`;
4. добавить в админку:
   - новый раздел со **всеми чатами пользователей**;
   - отображение **IP**, с которого шёл чат;
   - отображение **IP**, с которого запускалась генерация;
5. сделать это так, чтобы решение было:
   - архитектурно чистым,
   - совместимым с FSD,
   - удобным для Cursor,
   - пригодным для масштабируемого долгосрочного проекта.

Этот документ основан на реальном просмотре распакованных исходников:
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/widgets/stylist-chat-panel/ui/StylistChatPanel.tsx`
- `apps/frontend/src/widgets/chat-thread/ui/ChatThread.tsx`
- `apps/frontend/src/features/chat/ui/*`
- `apps/frontend/src/shared/ui/*`
- `apps/frontend/src/widgets/admin/ui/*`
- `apps/backend/app/models/*`
- `apps/backend/app/api/routes/*`
- `apps/backend/app/services/*`

---

# 1. Короткий вывод после анализа исходников

## 1.1. Текущее состояние frontend в целом хорошее по структуре, но слабое по визуальной системе

У проекта уже есть сильные стороны:
- frontend не хаотичный;
- FSD-подобная структура уже реально используется;
- chat, admin, entities, shared, widgets и features уже разведены;
- есть базовые reusable primitives:
  - `WindowFrame`
  - `InputSurface`
  - `SoftButton`
  - `RoundIconButton`
  - `ProgressRing`
- есть выделенные chat/process layers;
- есть отдельный admin shell;
- есть `StylistRuntimeSettingsManager` для лимитов и cooldown.

То есть проект **не надо переписывать с нуля**.

Но при этом визуально public UI сейчас действительно выглядит:
- слишком утилитарно;
- местами как “внутренний интерфейс”;
- недостаточно премиально;
- недостаточно цельно;
- без сильной общей дизайн-системы на уровне главной страницы.

---

## 1.2. Основная проблема не в одном chat panel, а в visual language всей главной страницы

Сейчас:
- `HomePageSurface.tsx` строит страницу как простую последовательность блоков:
  - Header
  - title + subtitle
  - ChatWindow
  - проекты
  - блог
  - about
- визуальный rhythm слабый;
- hero не ощущается как продуктовый центр;
- chat не ощущается как premium centerpiece;
- цвета, поверхности, отступы и visual hierarchy слишком “обычные”.

Поэтому redesign должен затронуть:
- **всю главную страницу**
- hero composition
- chat block
- project cards language
- blog cards / section transitions
- footer integration
- global tokens and surfaces

---

## 1.3. Admin тоже уже есть, но ему не хватает operational maturity

Текущее admin:
- уже имеет shell;
- уже имеет jobs, parser, settings и другие разделы;
- уже имеет runtime settings manager.

Но:
- нет раздела `Chats`;
- нет session-level audit view;
- нет chat IP visibility;
- generation jobs пока не показывают user IP;
- admin surfaces визуально слабее, чем могли бы быть.

---

# 2. Какие файлы сейчас являются ключевыми точками redesign

## 2.1. Public page / composition
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/widgets/header/ui/Header.tsx`
- `apps/frontend/src/widgets/footer/ui/Footer.tsx`
- `apps/frontend/src/widgets/about/ui/AboutSection.tsx`
- `apps/frontend/src/entities/project/ui/ProjectCardWindow.tsx`
- `apps/frontend/src/entities/blog-post/ui/BlogCard.tsx`

---

## 2.2. Chat UI
- `apps/frontend/src/widgets/stylist-chat-panel/ui/StylistChatPanel.tsx`
- `apps/frontend/src/widgets/chat-thread/ui/ChatThread.tsx`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`
- `apps/frontend/src/features/chat/ui/GenerationStatusRail.tsx`
- `apps/frontend/src/features/chat/ui/UploadArea.tsx`
- `apps/frontend/src/features/chat-cooldown/ui/ChatCooldownSendControl.tsx`
- `apps/frontend/src/shared/ui/InputSurface.tsx`
- `apps/frontend/src/shared/ui/SoftButton.tsx`
- `apps/frontend/src/shared/ui/RoundIconButton.tsx`
- `apps/frontend/src/shared/ui/ProgressRing.tsx`
- `apps/frontend/src/shared/ui/WindowFrame.tsx`

---

## 2.3. Global theme
- `apps/frontend/src/app/globals.css`
- `apps/frontend/tailwind.config.ts`

---

## 2.4. Admin UI
- `apps/frontend/src/widgets/admin/ui/AdminLayoutShell.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsTable.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsTableLive.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsControlPanel.tsx`
- `apps/frontend/src/widgets/admin/ui/SettingsManager.tsx`
- `apps/frontend/src/widgets/admin/ui/StylistRuntimeSettingsManager.tsx`
- `apps/frontend/src/app/admin/*`

---

## 2.5. Backend for admin/audit/IP
- `apps/backend/app/models/generation_job.py`
- `apps/backend/app/models/chat_message.py`
- `apps/backend/app/models/stylist_session_state.py`
- `apps/backend/app/repositories/generation_jobs.py`
- `apps/backend/app/repositories/chat_messages.py`
- `apps/backend/app/api/routes/stylist_chat.py`
- `apps/backend/app/api/routes/generation_jobs.py`
- `apps/backend/app/api/routes/stylist_runtime_settings.py`
- `apps/backend/app/services/stylist*.py`
- `apps/backend/app/services/generation.py`

---

# 3. Какой именно визуальный эффект нужен

## 3.1. Что нужно взять из Adobe Podcast Enhance как принцип, а не как копию

Референс хорош не потому, что там “фиолетовые блоки”, а потому что там:
- большие цельные поверхности;
- высокая ясность композиции;
- минимум визуального мусора;
- много воздуха;
- крупные радиусы;
- большие control-зоны;
- одна сильная фокусная область;
- интерфейс ощущается продуктовым, а не техническим.

Именно это нужно перенести в проект.

---

## 3.2. Что НЕ нужно копировать дословно
Не нужно:
- копировать audio-tool UX;
- копировать exact Adobe colors;
- копировать sliders;
- копировать layout 1-в-1.

Нужно:
- перенять surface grammar;
- перенять hierarchy;
- перенять premium calmness;
- перенять softness and confidence in layout.

---

# 4. Новый визуальный принцип главной страницы

## 4.1. Главная страница должна стать single cohesive product surface
Сейчас она выглядит как:
- title
- chat
- projects list
- blog list
- about

Нужно, чтобы она выглядела как:
- цельный premium personal AI product page,
- где chat — центральный элемент,
- а portfolio, blog и about поддерживают trust and context.

---

## 4.2. Новая иерархия главной страницы

### Блок 1. Header
Чище, легче, с большим воздухом.

### Блок 2. Hero / assistant stage
Крупный hero-комплекс:
- слева или сверху — headline и product promise;
- справа или ниже — главная assistant/chat surface;
- лёгкие info chips / trust badges.

### Блок 3. Project highlights
Не просто список карточек подряд, а более curated grid rhythm.

### Блок 4. Blog / content
Встроен мягче и чище.

### Блок 5. About / personal context
Не как “ещё один блок”, а как часть единой narrative page.

### Блок 6. Footer
Спокойный, воздух, меньше тяжести.

---

# 5. Новый дизайн-фундамент

## 5.1. Глобальная тема сейчас слишком бедная
Текущий `globals.css` содержит очень мало настоящих design tokens:

```css
:root {
  --color-background: #ffffff;
  --color-panel: #ffffff;
  --color-accent: #d0a46d;
  --color-sand: #f8f1e8;
  --color-ink: #101828;
  --color-muted: #667085;
}
```

Это слишком мало, чтобы построить сильный продуктовый UI.

---

## 5.2. Нужно ввести полноценную token system

### Рекомендуемые группы токенов:

#### Backgrounds
- `--bg-app`
- `--bg-canvas`
- `--bg-soft-grid`

#### Surfaces
- `--surface-primary`
- `--surface-secondary`
- `--surface-elevated`
- `--surface-lilac`
- `--surface-rose`
- `--surface-mint`
- `--surface-ink`

#### Text
- `--text-primary`
- `--text-secondary`
- `--text-muted`
- `--text-inverse`

#### Borders
- `--border-soft`
- `--border-strong`

#### Shadows
- `--shadow-soft-sm`
- `--shadow-soft-md`
- `--shadow-soft-xl`

#### Radius
- `--radius-panel`
- `--radius-control`
- `--radius-pill`
- `--radius-bubble`

#### Accents
- one brand accent
- support accent tones for states

---

## 5.3. Пример направления токенов

```css
:root {
  --bg-app: #f5f4f7;
  --bg-canvas: #fbfafc;

  --surface-primary: #ffffff;
  --surface-secondary: #f7f6fb;
  --surface-lilac: #efedff;
  --surface-rose: #fdeff5;
  --surface-mint: #eaf7ef;
  --surface-ink: #141416;

  --text-primary: #18181b;
  --text-secondary: #5f6470;
  --text-muted: #8b90a0;
  --text-inverse: #ffffff;

  --border-soft: rgba(24, 24, 27, 0.08);
  --border-strong: rgba(24, 24, 27, 0.14);

  --shadow-soft-md: 0 14px 38px rgba(15, 23, 42, 0.08);
  --shadow-soft-xl: 0 28px 80px rgba(15, 23, 42, 0.10);

  --radius-panel: 32px;
  --radius-control: 20px;
  --radius-pill: 999px;
  --radius-bubble: 24px;
}
```

---

## 5.4. Что менять в `globals.css`
Нужно:
- полностью усилить token layer;
- задать background для всей страницы;
- ввести reusable utility classes;
- выровнять spacing grammar;
- задать consistent scrollbar and focus states;
- улучшить `.page-shell`, чтобы страница чувствовалась более просторной.

---

# 6. Shared UI primitives: что нужно обновить и добавить

## 6.1. `WindowFrame.tsx`
Сейчас это полезный primitive, но он слишком общий и слабо типизирован по визуальным вариантам.

### Нужно:
- сделать `variant`:
  - `default`
  - `tinted`
  - `elevated`
  - `chat`
  - `admin`
- поддержать:
  - title area
  - subtitle area
  - action slot
  - footer slot
  - optional decorative tone

### Почему:
один `WindowFrame` должен стать основой surface language, а не просто белой коробкой.

---

## 6.2. `InputSurface.tsx`
Нужно переработать в более мощный primitive:
- bigger padding
- smoother radius
- support for dark action control
- support for inner footer / chips
- better disabled state
- better background contrast

---

## 6.3. `SoftButton.tsx`
Нужно:
- добавить tone variants:
  - `primary`
  - `neutral`
  - `subtle`
  - `accent`
  - `dark`
- shape variants:
  - `pill`
  - `surface`
  - `compact`
- clearer hover/pressed states
- consistent icon/text spacing

---

## 6.4. `ProgressRing.tsx`
Это ключевой компонент под новый send control.

Нужно:
- проверить текущую реализацию;
- усилить визуально:
  - smooth ring thickness
  - dark background support
  - white arc support
  - optional numeric countdown label
- использовать как главный reusable loader for cooldown states.

---

## 6.5. Новые компоненты в `shared/ui`
Нужно добавить:

### `SurfaceCard`
Большая панель с несколькими variant.

### `SectionHeader`
Для секций главной страницы и admin pages.

### `PillBadge`
Unified chips/statuses.

### `FloatingActionBar`
Если понадобится для bottom controls.

### `ChatModeChip`
Для статуса chat режима.

---

# 7. Redesign всей главной страницы

## 7.1. `HomePageSurface.tsx` — обязательный главный файл redesign
Сейчас он собирает страницу последовательно и сухо.

### Что нужно:
перестроить страницу как curated product landing / workspace.

---

## 7.2. Новая композиция `HomePageSurface`

### Section A — top page frame
- Header
- больше вертикального воздуха
- cleaner top rhythm

### Section B — Hero Assistant Stage
Должен стать **главным визуальным центром страницы**:
- большой title/subtitle area
- компактные supporting chips
- справа/ниже — main chat surface
- subtle decorative tinted surface behind or around it

### Section C — Featured projects
Не просто linear list.  
Нужна более curated layout rhythm:
- alternating windows
- better spacing
- stronger section intro

### Section D — Writing / Blog
Более редакционный блок, не просто карточки подряд.

### Section E — About
Мягче, с лучшей секцией и визуальным breathing space.

### Section F — Footer
Lightweight, calmer, less “just another block”.

---

## 7.3. Hero должен использовать chat как centerpiece
Сейчас chat — просто один section после title.

Нужно, чтобы пользователь уже в первом экране видел:
- это AI stylist product;
- это главный функциональный блок;
- он визуально premium.

---

# 8. Новый hero section

## 8.1. Сейчас есть `HeroSection.tsx`, но он не является фактическим центром home page
Сейчас hero отдельный и не встроен как dominant product stage.

---

## 8.2. Что делать
Либо:
- переработать `HeroSection.tsx` и реально встроить его в `HomePageSurface`,
либо
- собрать новый `HomeHeroAssistantStage`.

Я рекомендую второй вариант:
- старый `HeroSection` можно использовать как базу,
- но главный assistant-first hero лучше собрать отдельным widget.

---

## 8.3. Новый hero widget
Например:

`widgets/hero/ui/HomeHeroAssistantStage.tsx`

Внутри:
- heading area
- supporting copy
- quick benefits chips
- main chat surface
- optional small trust row

---

# 9. Redesign chat panel

## 9.1. `StylistChatPanel.tsx` — главный UI-узел
Его нужно **не просто перекрасить**, а **декомпозировать и пересобрать**.

---

## 9.2. Что сейчас в нём плохо
- много layout + logic вместе;
- визуально панель ощущается как “функциональный чат”, а не как polished premium assistant;
- status area / generation rail / composer / quick actions visual grammar ещё не unified.

---

## 9.3. Что нужно вынести
Новые подкомпоненты:

- `ChatAssistantHeader`
- `ChatConversationSurface`
- `ChatComposerDock`
- `ChatQuickActionsBar`
- `ChatGenerationDock`
- `ChatClarificationPanel`
- `ChatAttachedAssetChip`

---

## 9.4. Почему это важно
Cursor иначе может начать делать redesign “в одном giant component”, и дальше это будет трудно поддерживать.

---

# 10. Новый visual grammar chat panel

## 10.1. Верх панели
Нужен cleaner premium assistant header:
- assistant name
- assistant subtitle
- status pill
- optional mode indicator

Менее technical, больше product identity.

---

## 10.2. Центральная зона
Conversation should feel:
- spacious
- calm
- readable
- premium
- not messenger-debug-like

Нужно:
- больше padding
- мягче background
- лучшее разделение bubbles
- лучшее пустое состояние
- лучшее состояние загрузки

---

## 10.3. Нижняя зона
Composer должен стать отдельным “dock”:
- мягкий большой input surface
- внутри upload / textarea / send control
- ниже или рядом — quick actions / CTA
- generation rail integrated better

---

# 11. Redesign chat thread

## 11.1. `widgets/chat-thread/ui/ChatThread.tsx`
Нужно:
- улучшить spacing;
- усилить message bubbles;
- сделать assistant bubbles богаче, но не шумнее;
- user bubbles сделать чище и чуть проще;
- улучшить welcome state;
- улучшить pending / clarification display.

---

## 11.2. Assistant bubbles
Assistant bubbles можно сделать:
- светлыми tinted surfaces
- чуть более большими
- с лучшим line-height
- с мягким border/shadow

---

## 11.3. User bubbles
User bubbles:
- более плотные
- тёмнее/контрастнее
- но всё ещё мягкие и rounded

---

# 12. Send button → circular cooldown loader

## 12.1. Это требование сохраняется
Вместо стандартной send button должен использоваться:
- круговой loader/countdown
- 60 секунд после отправки
- black background
- white circular progress arc

---

## 12.2. Где это уже частично есть
В проекте уже есть:
- `features/chat-cooldown/ui/ChatCooldownSendControl.tsx`
- `shared/ui/ProgressRing.tsx`

То есть это не нужно придумывать с нуля — нужно **визуально и архитектурно усилить**.

---

## 12.3. Что нужно сделать
`ChatCooldownSendControl` должен стать:
- главным action control composer’а
- visually premium
- larger
- smoother
- more tactile

Нужно:
- усилить variant `dark`
- улучшить animation quality
- улучшить disabled / locked states
- optionally add minimal numeric center label

---

## 12.4. То же правило после `Попробовать другой стиль`
Control / cooldown logic must remain shared:
- send message cooldown
- try other style cooldown

UI может быть разный, но policy and visual language должны быть unified.

---

# 13. Quick actions и CTA redesign

## 13.1. Сейчас quick actions functional, but visually weak
Нужно:
- сделать их pill-shaped;
- менее “button row”, больше “assistant suggestions”;
- мягкие tinted chips;
- единая высота и padding.

---

## 13.2. Visualization CTA
CTA-кнопка должна:
- выглядеть как richer assistant offer;
- быть full-width surface;
- иметь clearer hierarchy;
- не выглядеть как обычная secondary button.

---

# 14. Generation status и result redesign

## 14.1. Сейчас generation result уже лучше, чем раньше
Есть:
- `GenerationResultCard`
- `GenerationStyleExplanation`

Это хорошо.

---

## 14.2. Что нужно улучшить
### `GenerationResultCard.tsx`
Сделать:
- richer presentation frame
- better image container
- calmer progress bar
- better typography in explanation area
- tighter alignment with new chat visual system

### `GenerationStyleExplanation.tsx`
Нужно убедиться, что:
- explanation block выглядит как editorial context card;
- не как raw technical metadata;
- лучше интегрирован под изображением.

---

## 14.3. Новый принцип
Когда generation completed:
- пользователь должен видеть не просто картинку,
- а маленькую curated editorial explanation card about the style.

---

# 15. Redesign projects / blog / about

## 15.1. Почему это обязательно
Ты прямо сказал: изменить надо **всю главную страницу**, а не только chat.

Это верно. Если изменить только chat:
- страница останется визуально разрозненной;
- новая chat surface будет конфликтовать со старым визуальным языком проекта.

---

## 15.2. `ProjectCardWindow.tsx`
Нужно:
- усилить surface grammar;
- обновить internal padding and radius;
- сделать cards visually closer to the new design language;
- уменьшить ощущение “window mockup ради window mockup”.

---

## 15.3. `BlogCard.tsx`
Нужно:
- сделать editorial cleaner cards;
- мягче фон/тени/радиусы;
- лучше типографика;
- лучше section rhythm.

---

## 15.4. `AboutSection.tsx`
Нужно:
- calmer presentation
- stronger section intro
- better spacing
- match overall premium visual system

---

# 16. Admin redesign

## 16.1. `AdminLayoutShell.tsx`
Сейчас shell workable, но слишком базовый.

### Нужно:
- обновить left nav surface;
- унифицировать page surfaces;
- улучшить header area;
- сделать admin более “control room premium”, а не просто список ссылок.

---

## 16.2. Добавить новый пункт меню
В `links` нужно добавить:
- `/admin/chats`
- key: `chats`

---

## 16.3. Новый раздел `/admin/chats`
Нужны:
- `app/admin/chats/page.tsx`
- `widgets/admin/ui/ChatSessionsTable.tsx`
- `widgets/admin/ui/ChatSessionDetailsPanel.tsx`

---

# 17. Что должно быть в новом разделе Chats

## 17.1. Таблица сессий
Поля:
- session id
- started at
- updated at
- message count
- locale
- current / last mode
- last decision type
- client IP
- short user-agent
- actions

---

## 17.2. Детали сессии
При открытии:
- messages
- generation jobs in this session
- current state snapshot
- IP
- user-agent
- timestamps

---

## 17.3. Почему нужен session-level admin view
Потому что operationally админу важнее:
- видеть разговор как единицу,
- а не raw list of all messages.

---

# 18. Что добавить в generation jobs admin

## 18.1. Сейчас jobs table слишком бедная
`GenerationJobsTable.tsx` показывает только:
- public id
- status
- progress
- result link

Этого недостаточно.

---

## 18.2. Нужно добавить:
- session id
- created at
- provider
- current operation / status text
- **client IP**
- short user-agent
- maybe recommendation preview
- error state clearly

---

## 18.3. Где менять
- `widgets/admin/ui/GenerationJobsTable.tsx`
- `widgets/admin/ui/GenerationJobsTableLive.tsx`
- `widgets/admin/ui/GenerationJobsControlPanel.tsx`
- frontend API types and client

---

# 19. Backend: что нужно добавить для IP tracking

## 19.1. Сейчас backend IP не хранит как полноценный audit layer
По моделям видно:
- `GenerationJob` не хранит IP
- `ChatMessage` тоже нет session-level IP metadata
- нет отдельной модели `chat_session_audit`

---

## 19.2. Нужно создать новую таблицу
### `stylist_chat_sessions`

Поля:
- `id`
- `session_id` unique
- `started_at`
- `updated_at`
- `last_message_at`
- `message_count`
- `locale`
- `client_ip`
- `client_user_agent`
- `last_active_mode`
- `last_decision_type`
- `metadata_json`

---

## 19.3. Зачем отдельная таблица
Это лучше, чем считать всё из `chat_messages`, потому что:
- быстрее для admin;
- чище по архитектуре;
- проще индексировать;
- проще расширять.

---

# 20. Backend: generation jobs IP

## 20.1. В `GenerationJob` нужно добавить
- `client_ip`
- `client_user_agent` optional
- maybe `request_origin`

---

## 20.2. Почему
Для:
- admin audit
- moderation / abuse analysis
- diagnostics
- operational transparency

---

# 21. Backend: как получать IP корректно

## 21.1. Нужен отдельный service/helper
`ClientRequestMetaResolver`

Он должен:
- читать `x-forwarded-for`
- читать `x-real-ip`
- fallback to `request.client.host`
- читать user-agent
- нормализовать результат

---

## 21.2. Где использовать
- public stylist chat route
- generation request creation
- future admin audit actions if needed

---

# 22. Backend: какие файлы менять

## 22.1. Models
- add new `stylist_chat_session.py`
- update `generation_job.py`

## 22.2. Repositories
- add `stylist_chat_sessions.py`
- extend `generation_jobs.py`

## 22.3. Routes
- `stylist_chat.py`
- `generation_jobs.py`
- add admin chat sessions route group

## 22.4. Services
- session metadata upsert on chat activity
- IP propagation into generation jobs
- request meta resolver

---

# 23. Frontend API changes

## 23.1. `shared/api/types.ts`
Добавить:
- `AdminChatSessionSummary`
- `AdminChatSessionDetails`
- `GenerationJob.client_ip`
- `GenerationJob.client_user_agent`

---

## 23.2. `shared/api/client.ts`
Добавить:
- `getAdminChatSessions`
- `getAdminChatSessionDetails`

И расширить generation jobs mapping.

---

# 24. Admin settings and existing cooldown/limits manager

## 24.1. Уже есть `StylistRuntimeSettingsManager`
Это хорошо.

### Значит:
- лимиты и cooldown уже не нужно придумывать заново;
- их надо **встроить в новый дизайн admin**
- и привести страницу настроек к новой visual system.

---

## 24.2. Что менять
- `SettingsManager.tsx`
- `StylistRuntimeSettingsManager.tsx`

Сделать:
- better grouping
- clearer labels
- better surfaces
- stronger information hierarchy
- match new admin design system

---

# 25. FSD-план изменений

## 25.1. Shared
### `shared/ui`
- redesign primitives
- `WindowFrame` v2
- stronger `InputSurface`
- stronger `SoftButton`
- stronger `ProgressRing`
- `SurfaceCard`
- `SectionHeader`
- `PillBadge`

### `shared/api`
- new admin session endpoints
- enriched generation job types

---

## 25.2. Entities
- `entities/chat-session`
- extend `entities/generation-job`
- keep `GenerationStyleExplanation`

---

## 25.3. Features
- `features/chat-cooldown`
- `features/admin-chat-filters`
- `features/admin-chat-session-view`
- `features/send-chat-message` visual integration

---

## 25.4. Widgets
- `widgets/stylist-chat-panel`
- `widgets/chat-thread`
- `widgets/admin/ui/ChatSessionsTable`
- `widgets/admin/ui/ChatSessionDetailsPanel`
- update admin jobs widgets
- new home hero widget if needed

---

## 25.5. App
- `app/HomePageSurface.tsx`
- `app/admin/chats/page.tsx`
- maybe adjust `app/page.tsx`

---

# 26. Clean Architecture / SOLID

## 26.1. SRP
- global theme отдельно
- public surfaces отдельно
- chat layout отдельно
- cooldown control отдельно
- admin session list отдельно
- admin session detail отдельно
- backend IP resolver отдельно
- session audit storage отдельно

---

## 26.2. OCP
Новые admin audit dimensions и новые public visual variants должны добавляться расширением, а не переписыванием всего page shell.

---

## 26.3. DIP
Frontend widgets должны зависеть от typed API contracts.

Backend routes должны зависеть от:
- services
- repositories
- request meta resolver

а не от inline DB logic.

---

# 27. Пошаговый план реализации

## Подэтап 1. Design foundation
- update `globals.css`
- add full token system
- improve tailwind token usage
- rework `WindowFrame`

## Подэтап 2. Shared UI primitives
- `SurfaceCard`
- `SectionHeader`
- `PillBadge`
- upgraded `InputSurface`
- upgraded `SoftButton`
- upgraded `ProgressRing`

## Подэтап 3. Whole homepage redesign
- restructure `HomePageSurface`
- new hero assistant stage
- align projects/blog/about with new visual grammar

## Подэтап 4. Chat redesign
- decompose `StylistChatPanel`
- improve `ChatThread`
- redesign composer
- keep and improve circular 60s loader
- integrate generation dock better

## Подэтап 5. Backend audit/IP
- add `stylist_chat_sessions`
- add generation IP fields
- add request meta resolver
- update routes/services

## Подэтап 6. Admin API
- list sessions endpoint
- session details endpoint
- enriched generation jobs DTO

## Подэтап 7. Admin frontend
- add `Chats` menu item
- create `/admin/chats`
- sessions table + details panel
- upgrade jobs page UI

## Подэтап 8. Admin settings UI polish
- integrate stylist runtime settings into stronger admin UI

## Подэтап 9. QA and regression
- responsive checks
- loading/empty/error states
- auth guards
- API compatibility
- visual polish pass

---

# 28. Acceptance criteria

Этап считается завершённым, если:

1. Дизайн изменён у **всей главной страницы**, а не только у chat panel.
2. Главная страница visually feels premium, spacious, calm and cohesive.
3. Chat — главный визуальный центр hero.
4. Все элементы чата rounded.
5. Круговой 60-second loader вместо send button сохранён и визуально улучшен.
6. Такой же cooldown сохраняется после `Попробовать другой стиль`.
7. Projects/blog/about visually согласованы с новым design language.
8. В admin есть новый раздел `Chats`.
9. Админ может видеть все chat sessions.
10. В chat sessions виден client IP.
11. В generation jobs виден client IP.
12. Backend корректно сохраняет и отдаёт IP metadata.
13. Решение уложено в FSD / OOP / SOLID / clean architecture.
14. Cursor может реализовывать изменения по файлам без хаоса.

---

# 29. Definition of Done

Работа считается выполненной корректно, если:
- публичная страница перестала выглядеть как набор функциональных блоков и стала целостным продуктовым интерфейсом;
- chat стал visually premium и сохранил cooldown behavior;
- admin стал operationally useful для просмотра user chats и generation IP;
- backend получил чистый audit/session metadata слой;
- архитектура осталась поддерживаемой и готовой к дальнейшему росту проекта.

---

# 30. Архитектурный итог

После реализации этого плана проект получает:

## На public side
- сильный redesign всей главной страницы
- premium assistant-first experience
- цельный surface language
- улучшенный chat with preserved cooldown UX

## На admin side
- новый chats audit section
- visibility of user IPs for chats and generations
- более зрелый control room

## На архитектурном уровне
- дизайн становится системным, а не “набором классов”
- admin/audit становится first-class частью продукта
- UI и backend лучше подготовлены к большому масштабируемому AI-проекту
