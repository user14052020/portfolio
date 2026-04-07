# Frontend Architecture And Improvements Plan

Этот файл фиксирует темы, которые обязательно нужно раскрыть во frontend-учебнике.

Важно: frontend нужно объяснять не только через React и Next.js, но и через базовую механику vanilla JavaScript в браузере. Иначе начинающий разработчик будет знать названия инструментов, но не поймёт, на чём они вообще стоят.

## 1. Обязательный фундамент перед React

### Базовая логика vanilla JavaScript

Нужно отдельно разобрать:
- переменные;
- функции;
- объекты и массивы;
- области видимости;
- замыкания;
- модули;
- события;
- `Promise`;
- `async/await`;
- `fetch`;
- DOM;
- browser event loop.

Нужно показать, что React не отменяет эти знания, а опирается на них.

### Что обязательно знать про браузер

Нужно объяснить:
- как загружается HTML;
- как браузер выполняет JavaScript;
- что такое DOM;
- как обрабатываются события;
- почему долгие операции тормозят интерфейс;
- как сетевой запрос доходит до API.

## 2. Что уже реализовано в проекте и почему

### FSD-подход в структуре фронта

Нужно подробно разобрать, что у нас frontend организован послойно:
- `app`
- `widgets`
- `features`
- `entities`
- `shared`
- `providers`
- `processes`

Ключевые пути:
- `apps/frontend/src/app`
- `apps/frontend/src/widgets`
- `apps/frontend/src/features`
- `apps/frontend/src/entities`
- `apps/frontend/src/shared`
- `apps/frontend/src/providers`
- `apps/frontend/src/processes`

Почему это важно:
- проект легче читать;
- проще понимать границы ответственности;
- легче масштабировать UI и не превращать всё в хаос.

### Tailwind CSS как выбранный styling-подход

Нужно подробно разобрать:
- utility-first подход;
- `tailwind.config.ts`;
- `globals.css`;
- `tailwind-merge`;
- почему стили живут рядом с компонентами через `className`.

Ключевые файлы:
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/src/app/globals.css`
- `apps/frontend/src/shared/lib/cn.ts`

### Централизованный API client

Нужно показать:
- почему сетевые вызовы не размазаны по UI-компонентам;
- почему есть `shared/api/client.ts`;
- как типы стабилизируют контракты.

Ключевые файлы:
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/shared/api/types.ts`
- `apps/frontend/src/shared/config/env.ts`

## 3. Что нужно отдельно раскрыть как улучшения frontend

### Архитектурные улучшения

Нужно обсуждать:
- где FSD соблюдён хорошо;
- где ещё остаются места для уплотнения границ;
- как не смешивать domain-логику, view-логику и network-логику.

### UI и UX улучшения

Нужно обсуждать:
- loading states;
- error states;
- disabled states;
- optimistic updates;
- polling UX;
- a11y и клавиатурную доступность;
- предсказуемое поведение форм.

### Производительность

Нужно отдельно объяснять:
- server/client boundaries;
- когда нужен SSR;
- когда нужна ленивная загрузка;
- как не тащить лишнюю логику в client-side;
- как сетевые запросы влияют на perceived performance.

## 4. Что ещё стоит включить как будущие улучшения frontend

- test strategy для hooks и UI;
- design tokens и унификация визуального слоя;
- error boundaries;
- более строгая форма типизации API-ответов;
- выделение повторяющихся UI-паттернов в shared/ui;
- системная документация по состояниям чата и генерации.

## 5. Обязательная формула будущих frontend-глав

Для каждой frontend-темы позже нужно писать:
1. База vanilla JavaScript, на которой это стоит.
2. Как это выражено в React/Next.
3. Как это конкретно реализовано в нашем проекте.
4. Какие архитектурные улучшения можно сделать дальше.
