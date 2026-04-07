# Что Такое next.config.mjs В Этом Проекте

После `package.json` и `tsconfig.json` следующий важный файл фронта — `next.config.mjs`.

Если:
- `package.json` отвечает за зависимости и команды,
- `tsconfig.json` отвечает за то, как TypeScript понимает код,

то `next.config.mjs` отвечает за то, **как именно ведёт себя сам Next.js в этом проекте**.

Основной файл:
- `apps/frontend/next.config.mjs:1-15`

Связанные файлы:
- `apps/frontend/package.json:5-10`
- `apps/frontend/tsconfig.json:32-39`
- `apps/frontend/src/entities/generation-job/ui/GenerationPreviewSurface.tsx:45-52`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultSurface.tsx:82-89`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultCard.tsx:73-80`

## Что Это Академически

`next.config.mjs` — это конфигурационный файл framework `Next.js`.

Он задаёт framework-level rules:
- как Next.js должен собирать приложение;
- какие runtime-опции включены;
- как работать с изображениями;
- куда складывать build artifacts;
- какие оптимизации и ограничения использовать.

Файл с расширением `.mjs` означает, что конфиг написан в формате **ES Modules**, а не в старом CommonJS-стиле.

## Что Это Простыми Словами

Если `package.json` — это паспорт frontend-пакета, то `next.config.mjs` — это панель настроек самого движка Next.js.

Он отвечает на вопросы:
- запускать ли React в более строгом режиме;
- куда класть build-результаты;
- какие внешние картинки разрешены;
- как framework должен вести себя при сборке и запуске.

## Чем next.config.mjs Отличается От Похожих Файлов

### next.config.mjs vs package.json

- `package.json` говорит, **какими командами** запускается Next.js и **что он установлен**.
- `next.config.mjs` говорит, **как именно настроен** Next.js.

В этом проекте:
- Next.js как зависимость: `apps/frontend/package.json:21`
- скрипты запуска: `apps/frontend/package.json:5-10`
- framework config: `apps/frontend/next.config.mjs:2-13`

### next.config.mjs vs tsconfig.json

- `tsconfig.json` отвечает за TypeScript.
- `next.config.mjs` отвечает за runtime/build-поведение Next.js.

Связь между ними есть, но роли разные:
- `apps/frontend/tsconfig.json:2-42`
- `apps/frontend/next.config.mjs:2-13`

### next.config.mjs vs Dockerfile

- `Dockerfile` описывает, как собрать и запустить контейнер.
- `next.config.mjs` описывает, как внутри этого запуска ведёт себя Next.js.

См.:
- `apps/frontend/Dockerfile:1-12`
- `apps/frontend/next.config.mjs:2-13`

## Почему Это Реализовано Именно Так

В этом проекте выбраны три настройки:
- `reactStrictMode: true`
- кастомный `distDir`
- `images.remotePatterns` с разрешением на внешние `https`-источники

Это решение выглядит небольшим, но на самом деле оно отражает важные архитектурные приоритеты:

1. Делать frontend строже в разработке, чтобы раньше замечать побочные эффекты.
2. Явно разделить dev и prod build output.
3. Разрешить работу с внешними изображениями на этапе MVP и интеграций.

## Что Реализовано В Этом Проекте

Реальный файл:
- `apps/frontend/next.config.mjs:1-15`

Содержимое:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: process.env.NODE_ENV === "production" ? ".next-production" : ".next-development",
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**"
      }
    ]
  }
};

export default nextConfig;
```

Ниже разбираем каждую часть.

## Разбор Файла По Строкам И Смыслам

### JSDoc-типизация конфига

См.:
- `apps/frontend/next.config.mjs:1`

Строка:
- `/** @type {import('next').NextConfig} */`

Что это значит:
- даже хотя файл написан не на TypeScript, IDE и tooling понимают ожидаемую форму объекта;
- это помогает автодополнению и снижает риск опечаток в ключах конфига.

Это хороший пример “типовой дисциплины” даже в обычном JS-конфиге.

### `reactStrictMode: true`

См.:
- `apps/frontend/next.config.mjs:3`

Что это значит:
- React strict mode включён.

Простыми словами:
- в development-окружении React становится более требовательным к побочным эффектам и подозрительным паттернам;
- он помогает раньше замечать неаккуратную логику компонентов.

Почему это полезно:
- фронт становится устойчивее;
- легче замечать проблемы с эффектами, состоянием и неочевидными побочными действиями;
- это особенно важно в сложных UI-сценариях вроде чата, polling и загрузки файлов.

Где это потенциально особенно важно в нашем проекте:
- `apps/frontend/src/features/chat/model/useStylistChatSimple.ts`
- `apps/frontend/src/shared/i18n/I18nProvider.tsx`
- `apps/frontend/src/features/admin-auth/model/useAdminAuth.ts`

### `distDir`

См.:
- `apps/frontend/next.config.mjs:4`

Значение:
- production build идёт в `.next-production`
- development build metadata идёт в `.next-development`

Почему это интересно:
- по умолчанию Next.js использует `.next`;
- здесь build output намеренно разделён по режимам.

Зачем это может быть полезно:
- меньше путаницы между development и production артефактами;
- легче понимать, какие generated files к какому режиму относятся;
- проще читать проект при наличии нескольких режимов запуска.

Очень важная связь:
- `apps/frontend/tsconfig.json:36-38`

TypeScript уже знает про:
- `.next/types/**/*.ts`
- `.next-development/types/**/*.ts`
- `.next-production/types/**/*.ts`

То есть `tsconfig.json` и `next.config.mjs` здесь уже согласованы между собой.

### `images.remotePatterns`

См.:
- `apps/frontend/next.config.mjs:5-12`

Что это значит:
- Next.js разрешено работать с внешними `https`-изображениями с любых hostnames.

Простыми словами:
- framework не ограничивает проект только локальными картинками;
- это полезно, если изображения приходят с внешних URL.

Где в проекте видно работу с `next/image`:
- `apps/frontend/src/entities/generation-job/ui/GenerationPreviewSurface.tsx:45-52`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultSurface.tsx:82-89`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultCard.tsx:73-80`

Важно:
- в этих местах сейчас используется `unoptimized`;
- значит текущая image-конфигурация не раскрывает всю свою силу в полном объёме;
- но она всё равно показывает выбранную политику: проект готов работать с внешними image URLs.

## Какие Anti-Patterns Рядом Существуют

### Anti-pattern 1. Вообще не иметь next.config и надеяться на дефолты

Это не всегда ошибка, но для серьёзного проекта быстро становится недостаточно.  
Как только появляются:
- внешние изображения;
- особые build outputs;
- runtime-правила;

framework config лучше делать явным.

### Anti-pattern 2. Делать слишком широкий image allowlist навсегда

Сейчас:
- `hostname: "**"` — `apps/frontend/next.config.mjs:9`

Для этапа активной интеграции это удобно.  
Но для production это слишком широкое разрешение.

Почему это риск:
- сложнее контролировать внешние источники изображений;
- сложнее проводить security-review;
- труднее понимать, какие домены реально нужны.

### Anti-pattern 3. Не синхронизировать distDir и tsconfig

Если поменять `distDir`, но забыть обновить `tsconfig include`, tooling может начать странно себя вести.

В нашем проекте это сделано аккуратно:
- `apps/frontend/next.config.mjs:4`
- `apps/frontend/tsconfig.json:36-38`

## Что Ещё Можно Улучшить

### 1. Ужесточить remote image policy

Вместо:
- любого `https` host

позже лучше оставить:
- только конкретные домены, которые реально нужны проекту.

### 2. Добавить явные пояснения к нестандартному distDir

Сейчас решение разумное, но для новичка неочевидное.  
В будущем можно дополнить это отдельным комментарием в коде или отдельным runtime-доком.

### 3. При необходимости расширить конфиг под production hardening

Позже здесь могут появиться темы:
- headers;
- redirects;
- rewrites;
- experimental flags;
- standalone output;
- image optimization policy.

## Где Это Видно В Реальном Потоке Работы

Когда разработчик запускает:

```bash
cd apps/frontend
npm run dev
```

происходит следующее:

1. npm запускает `next dev`.
2. Next.js читает `next.config.mjs`.
3. Включает `reactStrictMode`.
4. Выбирает `distDir` для текущего режима.
5. Подготавливает image policy.
6. Далее уже рендерит приложение и маршруты.

То есть `next.config.mjs` участвует в запуске очень рано, ещё до того, как вы увидите страницу в браузере.

## Команды

### Запуск фронта в dev-режиме

```bash
cd apps/frontend
npm run dev
```

### Production build

```bash
cd apps/frontend
npm run build
```

После этого стоит проверить, какой каталог build output появился:

```bash
cd apps/frontend
ls -la .next-development .next-production
```

На Windows PowerShell аналог:

```powershell
Get-ChildItem .next-development, .next-production -Force
```

## Мини-Упражнения

### Упражнение 1

Откройте `apps/frontend/next.config.mjs` и найдите:
- где включён strict mode;
- где настраивается каталог build output;
- где задаётся политика внешних изображений.

### Упражнение 2

Ответьте письменно:
- зачем нужен отдельный `next.config.mjs`, если уже есть `package.json`;
- почему `distDir` связан с `tsconfig.json`;
- почему `hostname: "**"` удобно на старте, но неидеально для production.

### Упражнение 3

Откройте:
- `apps/frontend/src/entities/generation-job/ui/GenerationPreviewSurface.tsx`
- `apps/frontend/src/entities/generation-job/ui/GenerationResultSurface.tsx`

И найдите:
- импорт `next/image`;
- использование `Image`;
- флаг `unoptimized`.

Подумайте, как это связано с image-настройками framework.

## Что Читать Дальше

После этой главы логично идти дальше так:
1. что такое vanilla JavaScript до React
2. что такое React
3. что такое FSD-структура фронта
4. что такое Tailwind CSS в этом проекте
