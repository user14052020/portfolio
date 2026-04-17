
# План redesign UI и админки проекта  
## Подробный implementation plan для Cursor  
## С учётом текущих исходников, FSD, OOP, SOLID, поддерживаемости и масштабируемости

## 0. Назначение документа

Этот документ описывает, **что и где менять в проекте**, чтобы:

1. сделать публичный chat UI визуально значительно сильнее, чище и приятнее — по уровню ощущения близко к референсу Adobe Podcast Enhance:
   - мягкие крупные радиусы,
   - спокойные большие поверхности,
   - ясная иерархия блоков,
   - меньше “технического интерфейса”,
   - больше ощущения premium assistant UI;
2. при этом **не сломать архитектуру** и не превратить redesign в “хаотичную перерисовку компонентов”;
3. добавить в админку:
   - новый раздел со **всеми чатами пользователей**;
   - возможность видеть **IP пользователя**, с которого шёл chat;
   - возможность видеть **IP пользователя**, с которого запускалась генерация;
4. сделать это так, чтобы решение было:
   - масштабируемым,
   - удобным для поддержки,
   - совместимым с текущим backend/frontend устройством,
   - аккуратным в рамках FSD / Clean Architecture / OOP / SOLID.

Документ опирается на фактическую структуру исходников в архиве:
- frontend: Next.js app router + FSD-like structure
- backend: FastAPI + SQLAlchemy + service/orchestrator architecture
- текущий chat UI, admin layout и generation/jobs admin already exist
- текущие модели `ChatMessage`, `GenerationJob`, `StylistSessionState` already exist
- в admin already есть `jobs`, `parser`, `projects`, `posts`, `contacts`, `settings`

---

# 1. Главный вывод после анализа исходников

## 1.1. Что видно по текущему фронтенду

Сейчас проект уже архитектурно неплохой:
- FSD-подобная структура реально соблюдается;
- chat уже вынесен в `widgets`, `features`, `entities`, `shared`;
- admin тоже вынесен в отдельные pages/widgets;
- базовый visual language уже есть:
  - rounded cards,
  - `WindowFrame`,
  - мягкие тени,
  - white panels.

Но визуально public chat сейчас действительно воспринимается как:
- функциональный,
- но **слишком утилитарный**;
- местами “debug-like”;
- не как polished premium assistant surface.

---

## 1.2. Основные проблемы текущего chat UI

По текущим файлам:

### `apps/frontend/src/widgets/stylist-chat-panel/ui/StylistChatPanel.tsx`
Сейчас там:
- много логики прямо в surface-компоненте;
- визуально блок похож на техническую панель;
- статус/entry/generation rail выглядят как набор внутренних control-блоков, а не как единый premium experience.

### `apps/frontend/src/app/globals.css`
Глобальная тема пока слишком базовая:
- почти нет полноценных design tokens;
- нет выраженного surface system;
- нет accent scale;
- нет отдельного conversational visual grammar.

### `apps/frontend/src/shared/ui/WindowFrame.tsx`
Это хороший компонент, но он ближе к “admin/project card language”, чем к тому лёгкому, просторному, мягкому и визуально дорогому интерфейсу, который ты хочешь.

### `HomePageSurface`
Сейчас чат вставлен как ещё один section block между проектами.  
Он функционален, но hero-композиция и visual breathing space пока не дают ощущения “центрального premium AI assistant”.

---

## 1.3. Что видно по backend/admin

### Уже есть:
- `/admin/jobs`
- `GenerationJobsControlPanel`
- `GenerationJobsTable`
- `GenerationJobsTableLive`
- auth / admin shell
- модели:
  - `ChatMessage`
  - `GenerationJob`
  - `StylistSessionState`

### Но пока нет:
- явной admin-страницы со списком chat sessions;
- хранения client IP для chat session / chat messages / generation jobs;
- admin API для просмотра chat sessions;
- расширения generation job DTO полем user IP.

---

# 2. Референсный дизайн: что именно надо брать из Adobe Podcast Enhance

Важно: задача не в том, чтобы копировать интерфейс 1-в-1.  
Задача — перенять **качественные дизайн-принципы**.

---

## 2.1. Какие принципы нужно перенять

### 1. Большие мягкие поверхности
Не много мелких карточек, а:
- несколько крупных блоков,
- чётко читаемая иерархия,
- воздух между секциями.

### 2. Высокие радиусы
Нужны:
- крупные скругления,
- спокойные rounded blocks,
- pill-shaped controls,
- более “tactile” UI.

### 3. Мягкий светлый фон + деликатные цветовые акценты
Не перегруженный стеклянный интерфейс и не “tailwind demo card system”, а:
- светлый чистый base,
- мягкие secondary surfaces,
- акцентные спокойные пастельные оттенки.

### 4. Одна сильная фокусная зона
У Adobe:
- upload block,
- central control area,
- bottom CTA bar.

У тебя аналогом должен стать:
- крупная chat surface,
- внутри — message area,
- нижняя control area,
- optional generation status / quick actions integrated visually, а не как separate debugging rails.

### 5. Меньше визуального шума
Нужно убирать:
- избыточные бордеры,
- много разных серых тонов,
- слишком много мелких технических лейблов,
- слишком плотную текстовую служебную информацию.

---

## 2.2. Что НЕ нужно копировать

Не надо:
- копировать Adobe colors 1-в-1;
- копировать exact slider language;
- копировать layout upload/audio controls;
- превращать fashion chat в “audio tool skin”.

Нужно копировать:
- уровень polish;
- surface hierarchy;
- interaction softness;
- visual clarity;
- ощущение premium calm interface.

---

# 3. Общая стратегия redesign

## 3.1. Нельзя делать redesign “точечно по месту”
Неправильный путь:
- подправить один className здесь,
- сменить пару rounded значений там,
- чуть поменять паддинги.

Так получится смесь старого и нового визуального языка.

---

## 3.2. Правильный путь
Нужно идти по слоям:

### Слой 1. Design tokens / theme foundation
Обновить:
- CSS variables
- surface scale
- radius scale
- shadow scale
- spacing rules
- semantic color tokens

### Слой 2. Shared primitives
Обновить/создать:
- `WindowFrame` v2
- `SurfaceCard`
- `PillBadge`
- `SectionHeader`
- `SoftButton`
- `IconButtonRound`
- `InputSurface`
- `FloatingActionBar`
- `ProgressRing`

### Слой 3. Chat composition
Пересобрать:
- `StylistChatPanel`
- thread
- input zone
- action zone
- status surfaces
- empty state / welcome state

### Слой 4. Admin redesign
Привести admin UI к более сильной системе:
- cleaner shell
- table cards
- filters
- side navigation
- unified panel system

### Слой 5. Data model / API additions
Добавить chat sessions view + IP tracking.

---

# 4. Целевой визуальный язык проекта

## 4.1. Public UI

Нужен стиль:
- premium minimal
- soft editorial tech
- spacious
- tactile
- calm
- not flashy
- not enterprise-gray

---

## 4.2. Основные принципы

### Base background
Очень светлый, почти молочный / холодный нейтральный.

### Primary surfaces
Белые или почти белые большие panels.

### Secondary surfaces
Очень мягкие tinted blocks:
- lavender / powder blue / pale mint / blush tints
- очень дозированно

### Accent usage
Один brand-accent + 2–3 semantic accents:
- success
- pending
- warning
- selection

### Borders
Тонкие, очень деликатные.  
Где возможно — заменять border на контраст surface и shadow depth.

### Shadows
Большие, мягкие, low-contrast shadows.  
Не резкие тени.

### Radius
Нужно ввести единую шкалу:
- panel radius
- button radius
- input radius
- badge radius
- media radius

---

# 5. Что конкретно нужно менять во frontend

## 5.1. `apps/frontend/src/app/globals.css`

Это первый обязательный файл redesign.

### Нужно сделать:
1. ввести полноценную систему CSS variables:
   - backgrounds
   - panel colors
   - tinted surfaces
   - accent colors
   - border colors
   - text hierarchy
   - shadow presets
   - radius scale
2. обновить `.page-shell`
3. добавить reusable utility classes:
   - `surface-primary`
   - `surface-secondary`
   - `surface-tint-*`
   - `shadow-soft-xl`
   - `radius-panel`
   - `radius-control`
   - `radius-pill`
   - `text-subtle`
   - `text-strong`
   - `focus-ring-soft`

### Нельзя:
- оставлять цветовую систему в виде 5 случайных root variables;
- продолжать строить дизайн только на `border-slate-200 bg-white`.

---

## 5.2. Новый набор design tokens

Рекомендуется добавить токены типа:

```css
:root {
  --bg-app: #f5f4f7;
  --bg-canvas: #fbfafc;
  --surface-primary: #ffffff;
  --surface-secondary: #f7f6fb;
  --surface-lilac: #efedff;
  --surface-pink: #fdeff5;
  --surface-mint: #e9f7ef;

  --text-primary: #18181b;
  --text-secondary: #5f6470;
  --text-muted: #878c98;

  --border-soft: rgba(24, 24, 27, 0.08);
  --border-strong: rgba(24, 24, 27, 0.14);

  --shadow-soft-md: 0 10px 30px rgba(15, 23, 42, 0.06);
  --shadow-soft-xl: 0 24px 80px rgba(15, 23, 42, 0.10);

  --radius-panel: 32px;
  --radius-control: 20px;
  --radius-pill: 999px;
}
```

---

## 5.3. `apps/frontend/src/shared/ui/WindowFrame.tsx`

Сейчас это хороший базовый компонент, но его нужно превратить в **системный public/admin surface primitive**.

### Нужно:
- сделать version 2 с вариантами:
  - `default`
  - `tinted`
  - `elevated`
  - `admin`
  - `chat`
- вынести вариативность в props:
  - `variant`
  - `padding`
  - `headerTone`
  - `footer`
- поддержать:
  - soft title area
  - subtle subtitle
  - action slot
  - optional footer slot

### Почему:
Сейчас `WindowFrame` слишком однообразен и не покрывает весь redesign system.

---

## 5.4. Новый shared primitive layer

Нужно создать/добавить компоненты в `src/shared/ui`:

### `SurfaceCard`
Универсальная панель.

### `SectionHeader`
Для заголовков внутри surfaces.

### `PillBadge`
Статусы:
- online
- generating
- offline
- active scenario

### `SoftButton`
Основная кнопка с premium rounded style.

### `RoundIconButton`
Кнопки-иконки.

### `InputSurface`
Обёртка для textarea/input со встроенным action area.

### `ProgressRing`
Для circular countdown / progress.

### `FloatingActionBar`
Bottom action strip, если нужен для chat actions / CTA.

---

# 6. Что конкретно менять в chat UI

## 6.1. Главный файл: `apps/frontend/src/widgets/stylist-chat-panel/ui/StylistChatPanel.tsx`

Это главный public chat surface и один из самых важных файлов redesign.

### Что сейчас плохо:
- слишком много layout + logic в одном component;
- визуально “debug-style control panel”;
- status, thread, input, scenario entry and generation rail собраны как набор технических секций.

### Что нужно:
Разделить этот компонент на:
- container layout
- header surface
- thread viewport
- assistant context strip
- scenario actions area
- input composer
- generation status dock

---

## 6.2. Целевая композиция chat panel

### Верхний блок
**Assistant header**
- assistant avatar / mark
- assistant name
- short subtle subtitle
- status badge
- optional “mode chip”

### Центральный блок
**Conversation surface**
- thread
- larger inner padding
- cleaner spacing between bubbles
- more editorial message rhythm

### Нижний блок
**Composer dock**
- integrated textarea
- upload / action controls
- circular send/cooldown control
- quick action pills
- generation CTA area

### Дополнительный блок
**Generation / queue / result status**
- встроенный как softer dock
- не должен выглядеть как debug admin widget

---

## 6.3. Что нужно вынести из `StylistChatPanel`

Создать новые UI-компоненты:

- `ChatAssistantHeader`
- `ChatConversationSurface`
- `ChatComposerDock`
- `ChatQuickActionsBar`
- `ChatGenerationDock`
- `ChatWelcomeCard`
- `ChatCooldownSendControl`

---

## 6.4. Почему это важно
Сейчас `StylistChatPanel` слишком большой и слишком “всё в одном”.  
Redesign без декомпозиции приведёт к хаосу.

---

# 7. Что менять в message thread

## 7.1. `apps/frontend/src/widgets/chat-thread/ui/ChatThread.tsx`

Этот компонент нужно визуально поднять.

### Нужно:
- увеличить расстояния между сообщениями;
- сделать пузырьки более продуманными:
  - larger radius
  - stronger contrast hierarchy
  - cleaner timestamp/meta treatment
- уменьшить ощущение “messenger debug UI”

### Рекомендуемая структура bubble:
- role-aware alignment
- role-aware surface
- larger text line-height
- optional subtle role marker
- support richer assistant blocks

---

## 7.2. Assistant bubbles

Assistant messages должны выглядеть:
- чуть богаче и спокойнее
- не как plain gray block
- с легким branded/tinted visual language

Можно:
- использовать очень слабый tinted background
- stronger padding
- better typography rhythm

---

## 7.3. User bubbles

User bubbles:
- чище
- проще
- контрастны, но не тяжелы
- rounded and compact

---

# 8. Что менять в composer

## 8.1. Текущий composer
Сейчас он функциональный, но визуально слабый.

---

## 8.2. Целевая модель
Composer должен стать:
- крупной мягкой surface
- со встроенным textarea
- с action pills
- с integrated circular send/cooldown control
- со status-aware disabled states

---

## 8.3. Новый UX control
После отправки — не обычная кнопка, а:
- круглый loader
- progress ring
- white arc on black fill or black capsule surface
- countdown label optional

И тот же control использовать после `Попробовать другой стиль`.

---

## 8.4. Новый компонент
`ChatCooldownSendControl`

Props:
- `isLocked`
- `secondsRemaining`
- `onSubmit`
- `variant`
- `disabledReason`

---

# 9. Что менять в generation status widgets

Текущие:
- `GarmentGenerationStatus`
- `OccasionGenerationStatus`
- `StyleGenerationStatus`

работают, но визуально ближе к внутренним control panels.

### Нужно:
- унифицировать их surface system;
- сделать:
  - softer cards
  - clearer progress hierarchy
  - one common visual grammar
- привести их к единому reusable base component:

`GenerationStatusCardBase`

От него специализации:
- garment
- occasion
- style

---

# 10. Что менять в home page composition

## 10.1. `apps/frontend/src/app/HomePageSurface.tsx`

Нужно переработать hero section с chat.

### Сейчас:
chat просто вставлен в section.

### Нужно:
сделать chat главным центром первой viewport-зоны:
- left/right or stacked hero layout;
- bigger breathing space;
- chat feels like centerpiece product experience.

---

## 10.2. Рекомендуемая структура
В hero:
- краткий headline
- короткий premium subcopy
- main assistant surface
- optional small trust/info chips beneath

---

## 10.3. Почему это важно
Если chat — главный продукт, он должен visually ощущаться главным.

---

# 11. Что менять в admin UI

## 11.1. `apps/frontend/src/widgets/admin/ui/AdminLayoutShell.tsx`

Admin уже выглядит прилично, но его тоже нужно привести к более зрелой системе.

### Нужно:
- сделать навигацию чище;
- улучшить spacing;
- сделать consistent surfaces;
- унифицировать page headers;
- улучшить page-level density.

---

## 11.2. Нужно добавить новую запись меню
В `links` нужно добавить новый раздел:

- `/admin/chats`
- key: `chats`

---

## 11.3. Новый admin раздел
Создать:

- `apps/frontend/src/app/admin/chats/page.tsx`
- `apps/frontend/src/widgets/admin/ui/ChatSessionsTable.tsx`
- возможно `ChatSessionDetailsPanel.tsx`

---

# 12. Что нужно добавить в админку по чатам

## 12.1. Новая задача
Админ должен видеть:
- все chat sessions
- сколько в них сообщений
- когда начаты
- когда обновлялись
- с какого IP шёл чат
- при необходимости — открывать детали

---

## 12.2. Рекомендуемый UI страницы `/admin/chats`
Нужны блоки:

### Верх
- page header
- subtitle
- фильтры

### Список/таблица
Колонки:
- session id
- started at
- updated at
- message count
- locale
- current mode
- last decision type
- client IP
- client user-agent short
- actions

### Правая панель / drawer / expandable card
Показывает:
- последние сообщения
- session context
- active mode
- attached jobs
- history

---

## 12.3. Почему это лучше, чем просто “таблица сообщений”
Потому что operationally админу важнее:
- sessions first
- then drill-down into messages

---

# 13. Что нужно добавить в раздел генераций

## 13.1. Сейчас generation jobs показываются без client IP
Это нужно исправить.

---

## 13.2. Что нужно видеть в admin jobs
Для каждого job:
- public id
- session id
- status
- progress
- created at
- current/last operation
- **client IP**
- possibly user-agent short
- result link
- error message

---

## 13.3. Где менять frontend
- `apps/frontend/src/widgets/admin/ui/GenerationJobsControlPanel.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsTable.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsTableLive.tsx`
- `apps/frontend/src/shared/api/types.ts`

---

# 14. Какие backend изменения нужны для IP tracking

## 14.1. Текущее состояние
Сейчас:
- `ChatMessage` не хранит IP
- `GenerationJob` не хранит IP
- routes не извлекают IP из request
- admin APIs не умеют отдавать session list with IP

---

## 14.2. Что нужно сделать архитектурно
Нельзя просто добавить `ip` в случайные payload поля.  
Нужно создать нормальную audit / session metadata модель.

---

# 15. Рекомендуемая backend модель для chat sessions

## 15.1. Проблема
Сейчас есть:
- `chat_messages`
- `stylist_session_states`

Но нет отдельной таблицы session metadata.

---

## 15.2. Нужно добавить новую таблицу
### `stylist_chat_sessions`

Поля:
- `id`
- `session_id` (unique)
- `started_at`
- `updated_at`
- `locale`
- `client_ip`
- `client_user_agent`
- `first_seen_path`
- `message_count`
- `last_message_at`
- `last_active_mode`
- `last_decision_type`
- `is_admin_session` bool nullable
- `metadata_json`

---

## 15.3. Почему это правильно
Это даёт:
- нормальный admin view
- не надо вычислять всё из сообщений
- можно расширять session analytics
- легче поддерживать и индексировать

---

# 16. Изменения в `ChatMessage`

## 16.1. Можно ли хранить IP прямо в `ChatMessage`?
Можно, но лучше не делать это основным способом.

### Рекомендуется:
- primary IP source = `stylist_chat_sessions.client_ip`
- optional denormalized `client_ip` in `chat_messages` only если нужен forensic granularity

### На данном этапе достаточно:
- session-level IP
- not per-message IP

---

# 17. Изменения в `GenerationJob`

## 17.1. Нужно добавить поля
В модель `GenerationJob`:

- `client_ip`
- `client_user_agent` (optional)
- `requested_by_role` optional
- `request_origin` optional

---

## 17.2. Почему это нужно
Потому что generation job может:
- быть создан из конкретного user session;
- быть важным для audit;
- быть нужен для abuse monitoring;
- отображаться в admin.

---

# 18. Какие backend файлы менять

## 18.1. Модели
- `apps/backend/app/models/generation_job.py`
- `apps/backend/app/models/chat_message.py` (если решишь добавлять denormalized ip)
- создать новый файл:
  - `apps/backend/app/models/stylist_chat_session.py`

---

## 18.2. Alembic migrations
Нужны новые migrations:
- add `client_ip`, `client_user_agent` to generation jobs
- create `stylist_chat_sessions`

---

## 18.3. Repositories
Создать:
- `apps/backend/app/repositories/stylist_chat_sessions.py`

Обновить:
- `generation_jobs.py`
- `chat_messages.py` if needed

---

## 18.4. API routes
Изменить:
- `apps/backend/app/api/routes/stylist_chat.py`
- `apps/backend/app/api/routes/generation_jobs.py`

Добавить новый admin route:
- `apps/backend/app/api/routes/admin_chat_sessions.py`  
или
- расширить admin router system отдельным endpoint group

---

## 18.5. Services
Изменить orchestrator/service flow:
- при первом сообщении создать/update session metadata
- при каждом сообщении обновлять `message_count`, `updated_at`, `last_active_mode`
- при generation creation пробрасывать `client_ip`

---

# 19. Как получать IP корректно

## 19.1. Нельзя слепо брать один заголовок
Нужно сделать отдельную утилиту / service:

`ClientRequestMetaResolver`

Он должен:
- уметь читать:
  - `x-forwarded-for`
  - `x-real-ip`
  - fallback на `request.client.host`
- нормализовать IP
- optionally trim proxy chains
- возвращать:
  - `client_ip`
  - `client_user_agent`

---

## 19.2. Где применять
- в `stylist_chat.py`
- в `generation_jobs.py`
- в future audit endpoints

---

# 20. Новый admin API для чатов

## 20.1. Нужны endpoints
### `GET /admin/chat-sessions`
Список с фильтрами:
- page
- page_size
- query
- session_id
- ip
- locale
- mode
- from_date
- to_date

### `GET /admin/chat-sessions/{session_id}`
Детали:
- session metadata
- session state
- messages
- generation jobs
- uploaded assets summary

---

## 20.2. Почему нужен отдельный endpoint слой
Потому что admin use-case сильно отличается от public chat API.

Нельзя использовать public `/stylist-chat/history/...` как основу админки.

---

# 21. Новые frontend API types

В `apps/frontend/src/shared/api/types.ts` нужно добавить:

- `AdminChatSessionSummary`
- `AdminChatSessionDetails`
- расширить `GenerationJob`:
  - `client_ip?: string | null`
  - `client_user_agent?: string | null`

---

## 21.1. Пример summary type

```ts
export interface AdminChatSessionSummary {
  session_id: string;
  started_at: string;
  updated_at: string;
  locale: string;
  message_count: number;
  last_active_mode?: string | null;
  last_decision_type?: string | null;
  client_ip?: string | null;
  client_user_agent?: string | null;
}
```

---

# 22. Новые frontend API client functions

В `apps/frontend/src/shared/api/client.ts` добавить:

- `getAdminChatSessions(token, params)`
- `getAdminChatSessionDetails(sessionId, token)`

И расширить mapping generation jobs.

---

# 23. Новый admin widget layer

## 23.1. Новый widget
`ChatSessionsTable`

Отвечает за:
- список сессий
- filter bar
- row selection
- empty state
- loading state
- error state

---

## 23.2. Новый widget
`ChatSessionDetailsPanel`

Показывает:
- summary
- messages
- generation jobs
- IP / user-agent
- current mode / context snapshot

---

## 23.3. Почему нужно два виджета
Это чище по FSD:
- list отдельно
- detail отдельно
- page их оркестрирует

---

# 24. Новый visual language для admin

## 24.1. Admin должен использовать ту же design system
Но:
- чуть плотнее
- чуть строже
- без потери премиальности

---

## 24.2. Что нужно сделать
Унифицировать admin surfaces:
- headers
- cards
- filters
- tables
- actions
- side nav

---

## 24.3. Таблицы лучше сделать не “голыми таблицами”
Лучше:
- responsive card-table hybrid
- или soft data grid style

Чтобы admin тоже выглядел современно, а не “внутренним кабинетом 2017”.

---

# 25. FSD-структура изменений

## 25.1. Shared
`src/shared/ui`
- новые primitives
- design system components

`src/shared/lib`
- utility classes / cn
- maybe theme helpers

`src/shared/api`
- types
- client
- admin chat session endpoints

---

## 25.2. Entities
Можно добавить:
- `entities/admin-chat-session`
- `entities/generation-job` расширить
- `entities/chat-session` расширить

---

## 25.3. Features
- `features/chat-cooldown`
- `features/chat-composer`
- `features/admin-chat-filters`
- `features/admin-chat-session-view`

---

## 25.4. Widgets
- `widgets/stylist-chat-panel`
- `widgets/chat-thread`
- `widgets/admin/ui/ChatSessionsTable`
- `widgets/admin/ui/ChatSessionDetailsPanel`
- `widgets/admin/ui/GenerationJobsControlPanel` update

---

## 25.5. App pages
- `/admin/chats/page.tsx`
- possibly update `/page.tsx` hero layout

---

# 26. Clean Architecture / SOLID

## 26.1. SRP
- design tokens отдельно
- shared UI primitives отдельно
- chat layout отдельно
- admin list отдельно
- admin detail separately
- backend request meta resolution отдельно
- session tracking отдельно
- generation audit enrichment отдельно

---

## 26.2. OCP
Новые admin sources и новые audit fields должны добавляться без переписывания core widgets.

---

## 26.3. DIP
Frontend widgets должны зависеть от typed API contracts, а не от raw fetch logic inside components.

Backend routes должны зависеть от:
- repositories
- services
- request meta resolver

а не от inline DB code everywhere.

---

# 27. Пошаговый план реализации

## Подэтап 1. Design foundation
- обновить `globals.css`
- ввести tokens
- ввести shadow/radius/surface system
- обновить `WindowFrame`

## Подэтап 2. Shared UI primitives
- `SurfaceCard`
- `SectionHeader`
- `PillBadge`
- `SoftButton`
- `RoundIconButton`
- `InputSurface`
- `ProgressRing`

## Подэтап 3. Chat redesign
- декомпозировать `StylistChatPanel`
- обновить thread UI
- обновить composer UI
- обновить status docks
- улучшить hero composition on home page

## Подэтап 4. Backend audit model
- добавить `stylist_chat_sessions`
- добавить IP fields в generation jobs
- сделать request meta resolver
- обновить services/repositories

## Подэтап 5. Admin API
- список chat sessions
- details endpoint
- generation job enriched DTO

## Подэтап 6. Admin frontend
- новый пункт меню `Chats`
- страница `/admin/chats`
- список + details panel
- обновить jobs panel с IP

## Подэтап 7. Polish and QA
- responsive checks
- empty states
- loading states
- auth guards
- regression testing

---

# 28. Acceptance criteria

Этап считается завершённым, если:

1. Public chat visually ощущается premium, clean и contemporary.
2. Новый UI использует единую design system, а не набор случайных классов.
3. `StylistChatPanel` декомпозирован на smaller UI blocks.
4. Message thread, composer, header и generation status визуально согласованы.
5. Home page hero подчёркивает chat как главный продукт.
6. В admin появляется новый раздел `Chats`.
7. Админ может видеть все chat sessions.
8. Для каждой chat session виден IP пользователя.
9. В admin jobs видно, с какого IP была запущена генерация.
10. Backend сохраняет и отдаёт client IP корректно.
11. Новые поля и страницы добавлены без архитектурного хаоса.
12. Решение удобно поддерживать и расширять.

---

# 29. Definition of Done

Работа считается выполненной корректно, если:
- UI перестал выглядеть как технический внутренний интерфейс и стал визуально сильным продуктовым surface;
- redesign не сломал архитектуру проекта;
- backend получил чистую audit-модель для chat sessions и generation IP;
- admin стал operationally useful;
- все изменения разложены по FSD / shared / widgets / features / app / backend services корректно;
- дальнейшее развитие дизайна и админки возможно без переписывания половины проекта.

---

# 30. Архитектурный итог

После реализации этого плана проект получает:

## На public side
- сильный premium UI
- более приятный chat experience
- визуально цельный assistant product

## На admin side
- полноценный operational control over chats
- visibility of user IP for chats and generations
- better moderation / audit / diagnostics surface

## На архитектурном уровне
- дизайн перестаёт быть “слоем поверх случайных className”
- admin перестаёт быть набором нескольких страниц без audit view
- UI и backend становятся лучше подготовлены к большому масштабируемому продукту
