# Frontend Roadmap

Этот блок объясняет клиентскую часть от самых базовых файлов до конкретных UI-сценариев.

## Учебные главы

### 01. Что такое JavaScript и зачем нужен TypeScript

Разобрать:
- JavaScript как язык браузера;
- TypeScript как надстройка;
- зачем нужна типизация;
- как типы помогают в этом проекте.

Ключевые файлы:
- `apps/frontend/package.json`
- `apps/frontend/tsconfig.json`
- `apps/frontend/src/shared/api/types.ts`

### 01a. Что обязательно знать про vanilla JavaScript до React

Разобрать:
- переменные и области видимости;
- функции и замыкания;
- массивы и объекты;
- модули;
- DOM;
- события;
- `Promise`;
- `async/await`;
- `fetch`;
- event loop браузера.

Ключевые файлы:
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/i18n/I18nProvider.tsx`
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`

Отдельная глава:
- [07-vanilla-javascript-browser-runtime.md](./07-vanilla-javascript-browser-runtime.md)

### 02. Что такое React

Разобрать:
- компонент;
- props;
- state;
- effect;
- hook;
- почему React вообще нужен.

Ключевые файлы:
- `apps/frontend/src/providers/AppProviders.tsx`
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`

### 03. Что такое Next.js

Разобрать:
- framework поверх React;
- маршрутизация;
- `app` directory;
- server/client boundaries;
- layout;
- page.

Ключевые файлы:
- `apps/frontend/src/app/layout.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/next.config.mjs`

Отдельные главы:
- [05-tsconfig-deep-dive.md](./05-tsconfig-deep-dive.md)
- [06-next-config-deep-dive.md](./06-next-config-deep-dive.md)

### 03a. SSR, SPA и hybrid rendering

Разобрать:
- что такое SSR;
- что такое SPA;
- что такое CSR;
- как Next.js сочетает несколько режимов;
- где в проекте страница серверная, а где логика уже активно клиентская.

Ключевые файлы:
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`

### 04. Что такое `package.json`

Разобрать:
- имя пакета;
- скрипты;
- зависимости;
- devDependencies;
- версия;
- зачем этот файл нужен Node ecosystem.

Ключевые файлы:
- `apps/frontend/package.json`

Отдельная глава:
- [04-package-json-deep-dive.md](./04-package-json-deep-dive.md)

### 05. Что такое стили и UI-слой

Разобрать:
- CSS;
- Tailwind;
- глобальные стили;
- utility classes;
- дизайн-система на уровне проекта.

Ключевые файлы:
- `apps/frontend/src/app/globals.css`
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/postcss.config.js`

### 06. Архитектура frontend в этом проекте

Разобрать:
- `app`
- `widgets`
- `features`
- `entities`
- `shared`
- `providers`
- `processes`

Файлы для разбора:
- `apps/frontend/src/app/*`
- `apps/frontend/src/widgets/*`
- `apps/frontend/src/features/*`
- `apps/frontend/src/entities/*`
- `apps/frontend/src/shared/*`

Отдельно пояснить:
- что это FSD-подход;
- почему фронт разделён на слои;
- какие границы между слоями нужно соблюдать.

### 06a. Что такое Tailwind CSS и почему он выбран

Разобрать:
- utility-first styling;
- как работает `tailwind.config.ts`;
- зачем нужен `globals.css`;
- почему в проекте много логики сидит в `className`;
- как `tailwind-merge` помогает не плодить конфликтующие классы.

Файлы:
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/shared/lib/cn.ts`

### 07. API client и типы

Разобрать:
- как frontend говорит с backend;
- что такое fetch wrapper;
- зачем отдельный `types.ts`;
- как обрабатываются ошибки.

Файлы:
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/api/types.ts`
- `apps/frontend/src/shared/config/env.ts`

### 08. Чат-ассистент на frontend

Разобрать:
- локальное состояние;
- optimistic UI;
- cooldown;
- polling generation jobs;
- file upload flow;
- quick actions.

Отдельно пояснить:
- почему сейчас используется polling;
- чем polling отличается от WebSockets;
- когда проекту может понадобиться real-time канал.

Файлы:
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`
- `apps/frontend/src/features/chat/ui/UploadArea.tsx`
- `apps/frontend/src/entities/generation-job/ui/GenerationPreviewSurface.tsx`

### 09. Админка

Разобрать:
- auth flow;
- менеджеры сущностей;
- generation job control panel.

Файлы:
- `apps/frontend/src/app/admin/*`
- `apps/frontend/src/features/admin-auth/*`
- `apps/frontend/src/widgets/admin/ui/*`

## Инвентаризация frontend-файлов по разделам

### Конфиги

- `apps/frontend/package.json`
- `apps/frontend/next.config.mjs`
- `apps/frontend/next-env.d.ts`
- `apps/frontend/tsconfig.json`
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/postcss.config.js`
- `apps/frontend/Dockerfile`

### App Router

- `apps/frontend/src/app/layout.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/app/admin/*`
- `apps/frontend/src/app/blog/*`
- `apps/frontend/src/app/projects/*`

### Feature layer

- `apps/frontend/src/features/chat/*`
- `apps/frontend/src/features/admin-auth/*`
- `apps/frontend/src/features/contact-request/*`
- `apps/frontend/src/features/content-search/*`

### Entity layer

- `apps/frontend/src/entities/blog-post/*`
- `apps/frontend/src/entities/project/*`
- `apps/frontend/src/entities/generation-job/*`

### Shared layer

- `apps/frontend/src/shared/api/*`
- `apps/frontend/src/shared/config/*`
- `apps/frontend/src/shared/i18n/*`
- `apps/frontend/src/shared/ui/*`
- `apps/frontend/src/shared/lib/*`
- `apps/frontend/src/shared/mock/*`

### Widgets

- `apps/frontend/src/widgets/about/*`
- `apps/frontend/src/widgets/admin/*`
- `apps/frontend/src/widgets/blog/*`
- `apps/frontend/src/widgets/footer/*`
- `apps/frontend/src/widgets/header/*`
- `apps/frontend/src/widgets/hero/*`
- `apps/frontend/src/widgets/portfolio/*`

## Что потом нужно разобрать построчно

- `apps/frontend/package.json`
- `apps/frontend/src/app/layout.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/api/types.ts`
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`

## Связанный план

- [02-frontend-file-atlas-plan.md](./02-frontend-file-atlas-plan.md) — подробная карта frontend-файлов для послойного разбора.
- [03-frontend-architecture-and-improvements-plan.md](./03-frontend-architecture-and-improvements-plan.md) — FSD, Tailwind, vanilla JS база и карта улучшений фронта.
