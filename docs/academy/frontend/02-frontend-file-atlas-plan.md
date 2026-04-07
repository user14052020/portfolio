# Frontend File Atlas Plan

Этот файл — план полного разбора frontend-файлов.

## 1. Корневые frontend-конфиги

Нужно разобрать:
- `apps/frontend/package.json`
- `apps/frontend/tsconfig.json`
- `apps/frontend/next.config.mjs`
- `apps/frontend/next-env.d.ts`
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/postcss.config.js`
- `apps/frontend/Dockerfile`

По каждому файлу нужно ответить:
- зачем он нужен;
- кто его читает;
- что в нём критично для запуска;
- что будет, если его сломать.

## 2. App Router entry files

Нужно разобрать:
- `apps/frontend/src/app/layout.tsx`
- `apps/frontend/src/app/page.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/app/admin/layout.tsx`
- `apps/frontend/src/app/admin/page.tsx`
- `apps/frontend/src/app/blog/page.tsx`
- `apps/frontend/src/app/projects/[slug]/page.tsx`

## 3. Providers и bootstrap

Нужно разобрать:
- `apps/frontend/src/providers/AppProviders.tsx`
- `apps/frontend/src/processes/bootstrap/init.ts`
- `apps/frontend/src/shared/i18n/I18nProvider.tsx`

## 4. Shared API and config

Нужно разобрать:
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/api/types.ts`
- `apps/frontend/src/shared/config/env.ts`

## 5. Chat feature

Нужно разобрать:
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`
- `apps/frontend/src/features/chat/ui/UploadArea.tsx`
- `apps/frontend/src/entities/generation-job/model/types.ts`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultSurface.tsx`

## 6. Admin feature set

Нужно разобрать:
- `apps/frontend/src/features/admin-auth/model/useAdminAuth.ts`
- `apps/frontend/src/features/admin-auth/ui/LoginForm.tsx`
- `apps/frontend/src/widgets/admin/ui/AdminDashboard.tsx`
- `apps/frontend/src/widgets/admin/ui/GenerationJobsControlPanel.tsx`
- остальные manager-компоненты админки

## 7. Page composition layer

Нужно разобрать:
- `apps/frontend/src/widgets/header/ui/Header.tsx`
- `apps/frontend/src/widgets/hero/ui/HeroSection.tsx`
- `apps/frontend/src/widgets/portfolio/ui/PortfolioGrid.tsx`
- `apps/frontend/src/widgets/blog/ui/BlogSection.tsx`
- `apps/frontend/src/widgets/footer/ui/Footer.tsx`

## Формат разбора одного frontend-файла

Для каждого файла позже нужно зафиксировать:
1. Тип файла.
2. Является ли он конфигом, компонентом, hook, helper или adapter.
3. Его входы: props, env, API calls, imports.
4. Его выходы: UI, side effects, network requests, exported types.
5. Как он связан с соседними файлами.
6. Какие строки и функции читать в первую очередь.
