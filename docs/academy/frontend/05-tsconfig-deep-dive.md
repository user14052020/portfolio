# Что Такое tsconfig.json В Этом Проекте

После `package.json` следующим логичным файлом для разбора становится `tsconfig.json`.  
Если `package.json` объясняет, какие инструменты вообще подключены к фронту, то `tsconfig.json` объясняет, **как именно TypeScript должен понимать этот код**.

Основной файл:
- `apps/frontend/tsconfig.json:1-43`

Связанный файл:
- `apps/frontend/next-env.d.ts:1-5`

## Что Это Академически

`tsconfig.json` — это конфигурационный файл TypeScript compiler.

Он задаёт:
- какие файлы входят в проект;
- по каким правилам TypeScript должен их анализировать;
- какие возможности языка включены;
- как разрешать модули;
- как обрабатывать JSX;
- должен ли TypeScript только проверять код или ещё и генерировать JavaScript.

Если говорить строго, `tsconfig.json` — это manifest правил компиляции и type-checking для TypeScript-проекта.

## Что Это Простыми Словами

Если представить TypeScript как очень внимательного технического редактора, то `tsconfig.json` — это инструкция для него:
- какие файлы ему разрешено читать;
- насколько он должен быть строгим;
- как понимать импорты;
- как относиться к React/JSX;
- должен ли он просто проверять код или ещё выпускать результат.

Без `tsconfig.json` TypeScript либо не поймёт проект как надо, либо будет использовать настройки по умолчанию, которые для Next.js-приложения почти всегда недостаточны.

## Чем tsconfig.json Отличается От Похожих Файлов

### tsconfig.json vs package.json

- `package.json` отвечает за зависимости и команды.
- `tsconfig.json` отвечает за правила анализа TypeScript-кода.

В этом проекте:
- TypeScript как инструмент подключён в `apps/frontend/package.json:27-36`
- правила TypeScript лежат в `apps/frontend/tsconfig.json:2-42`

### tsconfig.json vs next.config.mjs

- `tsconfig.json` говорит, как понимать TypeScript и JSX.
- `next.config.mjs` говорит, как настроен сам Next.js runtime.

В этом проекте:
- `apps/frontend/next.config.mjs:2-13`
- `apps/frontend/tsconfig.json:2-42`

### tsconfig.json vs next-env.d.ts

- `tsconfig.json` — это правила проекта.
- `next-env.d.ts` — вспомогательный файл, который подтягивает типы Next.js.

См.:
- `apps/frontend/next-env.d.ts:1-5`

TypeScript смотрит на этот файл потому, что он включён в список `include`:
- `apps/frontend/tsconfig.json:32-39`

## Зачем Это Нужно В Этом Проекте

Для frontend-части `portfolio` этот файл нужен, чтобы:
- включить строгую типизацию;
- корректно работать с React и JSX;
- понимать алиасы вида `@/shared/...`;
- дружить с Next.js plugin и внутренними типами Next;
- не генерировать JavaScript отдельно, потому что сборкой управляет Next.js;
- одинаково понимать проект локально и внутри toolchain.

Без него:
- импорты `@/...` перестанут работать как ожидается;
- TypeScript не сможет корректно анализировать `tsx`-файлы;
- Next.js потеряет часть интеграции с типами;
- многие ошибки будут выявляться позже или не выявляться вовсе.

## Где Это Видно В Коде Проекта

### 1. Алиасы `@/`

В `tsconfig.json` настроено:
- `baseUrl`: `apps/frontend/tsconfig.json:25`
- `paths`: `apps/frontend/tsconfig.json:26-30`

Именно это позволяет писать импорты вроде:
- `apps/frontend/src/shared/api/client.ts:1`
- `apps/frontend/src/providers/AppProviders.tsx:6-7`
- `apps/frontend/src/app/HomePageSurface.tsx:7-14`

Без `paths` и `baseUrl` пришлось бы писать длинные относительные пути вроде:
- `../../shared/api/client`
- `../../../widgets/header/ui/Header`

### 2. JSX и React-компоненты

В проекте много `.tsx`-файлов, например:
- `apps/frontend/src/providers/AppProviders.tsx:18-30`
- `apps/frontend/src/app/HomePageSurface.tsx:42-101`

TypeScript понимает их как React/JSX благодаря настройке:
- `jsx: "preserve"` — `apps/frontend/tsconfig.json:18`

### 3. Типизация API и UI

В проекте много явных типов, например:
- `apps/frontend/src/shared/api/client.ts:14-21`
- `apps/frontend/src/shared/api/client.ts:36`
- `apps/frontend/src/providers/AppProviders.tsx:18-24`

Это нормально работает только потому, что TypeScript включён и проект собран как полноценный TypeScript frontend.

## Разбор tsconfig.json По Полям

Ниже идём сверху вниз по реальному файлу.

## `target`

См.:
- `apps/frontend/tsconfig.json:3`

Значение:
- `ES2022`

Что это значит:
- TypeScript ориентируется на современные возможности JavaScript;
- код проекта описывается как современный JS, а не как старый стандарт времён ES5.

Это важно, потому что проект использует современный стек и не целится в очень старые среды.

## `lib`

См.:
- `apps/frontend/tsconfig.json:4-8`

Значения:
- `dom`
- `dom.iterable`
- `es2022`

Что это значит:
- TypeScript знает про браузерный DOM;
- знает про браузерные iterable-API;
- знает про современные возможности JavaScript.

Это критично для frontend, потому что здесь есть:
- `fetch`
- `window`
- `document`-подобные browser API
- React-компоненты, работающие в браузере

## `allowJs`

См.:
- `apps/frontend/tsconfig.json:9`

Значение:
- `false`

Что это значит:
- проект не предполагает, что обычные `.js`-файлы будут жить рядом с `.ts/.tsx` как равноправная часть кодовой базы.

Это повышает дисциплину:
- фронт пишется именно как TypeScript-проект;
- не возникает хаотичной смеси JS и TS.

## `skipLibCheck`

См.:
- `apps/frontend/tsconfig.json:10`

Значение:
- `true`

Что это значит:
- TypeScript не будет глубоко проверять типы внутри внешних библиотек.

Почему это часто ставят:
- ускоряет type-check;
- уменьшает шум от чужих типов;
- позволяет сосредоточиться на коде проекта.

Компромисс:
- если у сторонней библиотеки плохие типы, ошибка может не проявиться так рано.

## `strict`

См.:
- `apps/frontend/tsconfig.json:11`

Значение:
- `true`

Это одна из самых важных опций в файле.

Что она делает:
- включает строгий режим TypeScript;
- заставляет код точнее описывать значения и их возможные состояния;
- помогает ловить ошибки до запуска приложения.

Для production-minded frontend это хорошая базовая настройка.

## `noEmit`

См.:
- `apps/frontend/tsconfig.json:12`

Значение:
- `true`

Что это значит:
- TypeScript в этом проекте не должен сам выпускать `.js`-файлы.

Почему так:
- сборкой занимается Next.js;
- TypeScript здесь используется как система типов и проверки, а не как отдельный emit-компилятор.

Это важная мысль для новичка:
- TypeScript не обязан сам “производить JS” в каждом проекте;
- иногда его главная роль — проверка типов внутри более крупного toolchain.

## `esModuleInterop`

См.:
- `apps/frontend/tsconfig.json:13`

Значение:
- `true`

Что это даёт:
- более предсказуемую совместимость между разными стилями модулей;
- меньше боли при импортах из экосистемы npm.

## `module`

См.:
- `apps/frontend/tsconfig.json:14`

Значение:
- `esnext`

Что это значит:
- проект ориентируется на современную модульную модель JavaScript;
- это хорошо сочетается с современными bundler/runtime-инструментами.

## `moduleResolution`

См.:
- `apps/frontend/tsconfig.json:15`

Значение:
- `bundler`

Почему это важно:
- TypeScript разрешает модули так, как это ожидается в современном bundler-oriented окружении;
- это хорошо подходит для Next.js 14 и современной экосистемы ESM.

## `resolveJsonModule`

См.:
- `apps/frontend/tsconfig.json:16`

Значение:
- `true`

Что это даёт:
- TypeScript может понимать `import ... from "./file.json"`.

Даже если это сейчас не центральная часть проекта, опция полезна и соответствует современной frontend-практике.

## `isolatedModules`

См.:
- `apps/frontend/tsconfig.json:17`

Значение:
- `true`

Что это значит:
- каждый модуль должен быть достаточно “самостоятельным”, чтобы tooling мог обрабатывать его отдельно.

Для Next.js и современного toolchain это правильная опора.

## `jsx`

См.:
- `apps/frontend/tsconfig.json:18`

Значение:
- `preserve`

Что это значит:
- JSX не преобразуется самим TypeScript в финальный JS на этом этапе;
- JSX сохраняется для следующего шага toolchain, которым в проекте управляет Next.js.

То есть:
- TypeScript понимает JSX;
- но не он решает финальный build pipeline.

## `incremental`

См.:
- `apps/frontend/tsconfig.json:19`

Значение:
- `true`

Что это даёт:
- ускоряет повторные проверки проекта;
- tooling может сохранять промежуточную информацию и не анализировать всё заново каждый раз.

## `plugins`

См.:
- `apps/frontend/tsconfig.json:20-24`

Значение:
- plugin `next`

Почему это важно:
- TypeScript-aware tooling получает дополнительное понимание Next.js-контекста;
- это часть нормальной интеграции фронта с Next.

## `baseUrl` и `paths`

См.:
- `apps/frontend/tsconfig.json:25-30`

Это один из самых практических кусков файла.

Здесь задано:
- базовая точка разрешения модулей;
- алиас `@/* -> ./src/*`

Это позволяет писать:
- `@/shared/api/client`
- `@/widgets/header/ui/Header`
- `@/features/chat/ui/ChatWindowSimpleSurface`

Примеры из проекта:
- `apps/frontend/src/shared/api/client.ts:1-12`
- `apps/frontend/src/providers/AppProviders.tsx:6-7`
- `apps/frontend/src/app/HomePageSurface.tsx:7-17`

Это не просто “удобная косметика”.  
Это ещё и архитектурный инструмент:
- код читается легче;
- слои FSD лучше видны;
- импорты менее хрупкие при переносе файлов.

## `include`

См.:
- `apps/frontend/tsconfig.json:32-39`

Что сюда входит:
- `next-env.d.ts`
- все `*.ts`
- все `*.tsx`
- сгенерированные типы `.next/...`

Это значит, что TypeScript знает не только про исходники, но и про часть типовой информации, которую формирует сам Next.js.

## `exclude`

См.:
- `apps/frontend/tsconfig.json:40-42`

Здесь исключён:
- `node_modules`

Это стандартная и правильная настройка:
- код внешних библиотек не должен становиться частью исходного дерева проекта.

## Что Делает next-env.d.ts

См.:
- `apps/frontend/next-env.d.ts:1-5`

Этот файл:
- подтягивает типы Next.js;
- не должен редактироваться вручную;
- нужен для корректной TypeScript-интеграции Next-проекта.

Важно:
- это не “случайный мусорный файл”;
- это часть нормального TypeScript-контура Next.js.

## Как tsconfig.json Влияет На Реальную Разработку

Когда разработчик открывает фронт-проект в IDE, происходит примерно следующее:

1. IDE видит `tsconfig.json`.
2. Понимает, что проект строгий и TypeScript-first.
3. Читает `baseUrl` и `paths`.
4. Разрешает импорты `@/...`.
5. Читает `next-env.d.ts`.
6. Подключает Next.js-типизацию.
7. Проверяет `.ts` и `.tsx` по правилам `strict`.

Из-за этого:
- IDE умеет подсказывать типы;
- легче делать рефакторинг;
- ошибки видно до запуска приложения.

## Какие Команды Здесь Нужно Знать

### Показать итоговую конфигурацию TypeScript

```bash
cd apps/frontend
npx tsc --showConfig
```

### Прогнать type-check без emit

```bash
cd apps/frontend
npx tsc --noEmit
```

### Проверить, что алиасы и импорты согласованы

```bash
cd apps/frontend
npx tsc --noEmit --pretty
```

## Какие Anti-Patterns Здесь Нужно Понимать

### Anti-pattern 1. Считать, что tsconfig нужен только “ради типов”

Нет.  
Он влияет ещё и на:
- понимание JSX;
- модульную систему;
- алиасы импортов;
- интеграцию с Next.js.

### Anti-pattern 2. Убрать strict “чтобы ошибки не мешали”

Так можно сделать жизнь тише на пять минут, но дороже в поддержке дальше.  
Для production-oriented проекта строгий режим почти всегда лучше, чем “давайте ослабим всё”.

### Anti-pattern 3. Использовать длинные относительные импорты вместо продуманного alias layer

Если убрать `paths`, код станет:
- шумнее;
- хрупче при переносе файлов;
- тяжелее для чтения.

### Anti-pattern 4. Редактировать next-env.d.ts вручную

Файл сам подчинён Next.js-tooling.  
Правильнее менять настройки через нормальные конфиги, а не через ручную правку generated-support файла.

## Что В Этом Проекте Уже Сделано Хорошо

- включён `strict`;
- настроены алиасы `@/*`;
- есть корректная интеграция с Next plugin;
- `noEmit: true` хорошо соответствует Next.js pipeline;
- `.ts` и `.tsx` включены явно;
- `node_modules` исключены;
- используется современный target и модульная схема.

## Что Ещё Можно Улучшить

1. Позже можно рассмотреть ещё более строгие флаги вроде:
   - `noUncheckedIndexedAccess`
   - `exactOptionalPropertyTypes`
2. Можно отдельно задокументировать policy по алиасам и слоям FSD.
3. При росте проекта можно рассмотреть вынос общей TypeScript-базы в отдельный shared config, если появятся дополнительные frontend packages.

## Мини-Упражнения

### Упражнение 1

Найдите в `tsconfig.json`:
- где включён строгий режим;
- где настраивается JSX;
- где задаётся alias `@/*`;
- где указывается `next-env.d.ts`.

### Упражнение 2

Ответьте письменно:
- почему `noEmit: true` не мешает проекту собираться;
- зачем нужен `paths`;
- чем `tsconfig.json` отличается от `package.json`.

### Упражнение 3

Откройте:
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/providers/AppProviders.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`

И найдите в них импорты, которые работают благодаря `@/*`.

## Что Читать Дальше

После этой главы логично идти в таком порядке:
1. `next.config.mjs`
2. `что такое React`
3. `что такое vanilla JavaScript до React`
4. `что такое FSD-структура фронта`
