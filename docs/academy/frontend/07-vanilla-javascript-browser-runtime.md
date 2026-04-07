# Что Нужно Знать Про Vanilla JavaScript До React

Эта глава нужна, чтобы не возникало иллюзии, будто frontend начинается с React.  
На самом деле React, Next.js и даже TypeScript стоят на фундаменте обычного JavaScript и браузерного рантайма.

Если не понимать этот фундамент, то:
- `useState` кажется магией;
- `useEffect` кажется странным ритуалом;
- `fetch` кажется “просто вызовом API”;
- ошибки с асинхронностью начинают выглядеть случайными.

## Что Это Академически

`JavaScript` — это язык программирования общего назначения, который в контексте браузера выполняется внутри browser runtime.

`Vanilla JavaScript` — это JavaScript без framework-надстроек, когда вы опираетесь напрямую на:
- сам язык;
- браузерные API;
- DOM;
- события;
- таймеры;
- `Promise`;
- `fetch`.

`Browser runtime` — это среда выполнения, которая:
- исполняет JavaScript;
- даёт доступ к DOM, событиям, таймерам и сети;
- координирует выполнение задач через event loop.

## Что Это Простыми Словами

JavaScript — это язык, на котором браузеру говорят, что делать.

React не заменяет JavaScript.  
Он лишь помогает структурировать UI, но внутри всё равно живут:
- переменные;
- функции;
- объекты;
- события;
- асинхронные запросы;
- обновление состояния;
- работа с временем и очередями задач.

Если очень упростить:
- браузер показывает страницу;
- JavaScript реагирует на действия пользователя и сетевые ответы;
- React просто делает этот процесс более управляемым.

## Чем Vanilla JavaScript Отличается От React

- Vanilla JavaScript — это базовый язык и browser API.
- React — это библиотека поверх JavaScript.

Vanilla JavaScript отвечает за фундамент:
- функции;
- массивы;
- объекты;
- `Promise`;
- `async/await`;
- обработчики событий;
- DOM;
- `fetch`.

React добавляет:
- компоненты;
- state;
- declarative rendering;
- lifecycle через hooks.

Очень важно:
- React-компоненты всё равно написаны на JavaScript и TypeScript;
- `useState`, `useEffect`, обработчики `onClick` и `onChange` не отменяют знания про функции, замыкания, асинхронность и события.

## Почему Это Важно Именно В Этом Проекте

В нашем frontend это видно буквально везде:

### Работа с событиями

См.:
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L294)
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L295)
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L313)

Там есть:
- `onChange`
- `onKeyDown`
- `onClick`

Это не “React-магия”, а обычная event-driven модель интерфейса.

### Работа с асинхронными запросами

См.:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L36)
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L47)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L245)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L315)

Там есть:
- `async function`
- `await fetch(...)`
- `await getChatHistory(...)`
- `await getGenerationJob(...)`

Это чистая JavaScript-асинхронность, а не что-то специфически “реактовое”.

### Работа с локальным состоянием и замыканиями

См.:
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L31)
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L41)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L214)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L337)

Да, это React hooks, но underneath там всё равно:
- переменные;
- функции;
- области видимости;
- захват значений замыканием.

## База, Которую Нужно Понимать

## 1. Переменные и области видимости

JavaScript хранит значения в переменных.  
Важно понимать:
- где переменная создана;
- где она видна;
- когда она перестаёт быть доступной.

В реальном коде:
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L142)
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L160)

Здесь переменные вроде `quickActions`, `statusBadge`, `isCooldownActive` существуют внутри функции компонента и пересчитываются при новом рендере.

## 2. Функции

Функция — это блок логики, который можно вызвать.

В проекте функций очень много:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L23)
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L36)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L35)
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L19)

React-компонент тоже функция:
- [AppProviders.tsx](c:/dev/portfolio/apps/frontend/src/providers/AppProviders.tsx#L18)
- [HomePageSurface.tsx](c:/dev/portfolio/apps/frontend/src/app/HomePageSurface.tsx#L42)

## 3. Объекты и массивы

JavaScript интенсивно использует:
- объекты для хранения структурированных данных;
- массивы для коллекций.

Примеры:
- `RequestOptions` и payload-объекты в [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L14)
- массив `quickActions` в [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L32)
- массив сообщений в [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L214)

## 4. События

Браузерный UI работает по event-driven модели:
- пользователь нажал кнопку;
- ввёл текст;
- выбрал файл;
- пришёл сетевой ответ.

Примеры в проекте:
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L271)
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L294)
- [UploadArea.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/UploadArea.tsx)

Очень важно понимать:
- обработчик события — это обычная функция;
- внутри неё вы работаете с объектом события;
- затем меняете состояние или запускаете запрос.

## 5. Promise

`Promise` — это объект, который представляет результат асинхронной операции в будущем.

Пример из проекта:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L36)

Там `request<T>(...)` возвращает `Promise<T>`.

Это значит:
- результат есть не сразу;
- его нужно `await`-ить или обрабатывать через `.then()`.

## 6. async / await

`async/await` — удобный способ работать с `Promise`, не переписывая всё на цепочки `.then(...)`.

Примеры:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L36)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L337)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L440)

Очень важно:
- `await` не делает код “синхронным по-настоящему”;
- он просто позволяет писать асинхронную логику более читаемо.

## 7. fetch

`fetch` — это browser API для HTTP-запросов.

В проекте он обёрнут в централизованный клиент:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts#L47)

Но внутри это всё равно обычный `fetch`, который:
- делает запрос;
- ждёт ответ;
- превращает ответ в JSON;
- выбрасывает ошибку, если что-то пошло не так.

## 8. DOM

DOM — это объектное представление HTML-страницы в браузере.

Даже если вы работаете через React, браузер всё равно в конце оперирует DOM.

В проекте есть прямые прикосновения к браузерной среде:
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L21)
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L38)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L60)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L81)

Там видно:
- `document.cookie`
- `document.documentElement.lang`
- `window.localStorage`

Это уже не просто “React-мир”, а прямой контакт с browser runtime.

## 9. Event Loop

Event loop — это механизм, который координирует выполнение задач, колбэков, таймеров и обработку асинхронных результатов.

Примеры в проекте:
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L299)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L313)

Там используются:
- `window.setInterval(...)`
- асинхронный polling

Это очень хороший пример того, что frontend живёт не “по строчкам сверху вниз один раз”, а в непрерывном цикле:
- пользователь что-то делает;
- браузер что-то ждёт;
- таймер срабатывает;
- приходит сетевой ответ;
- интерфейс перерисовывается.

## Почему React Не Отменяет Эти Знания

Например, в [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L31) у нас есть `useState`, а в [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L33) и [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx#L37) — `useEffect`.

Но чтобы реально понимать этот код, нужно знать:
- что такое функция;
- что такое замыкание;
- что такое зависимость эффекта;
- что такое browser side effect;
- почему запись в `localStorage` и `document.cookie` — это не просто “что-то реактовое”, а взаимодействие с внешней средой.

То же самое в чате:
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx#L295)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts#L469)

Нажатие Enter запускает отправку сообщения, но за этим стоят:
- событие клавиатуры;
- обработчик;
- асинхронный вызов;
- сетевой запрос;
- обновление состояния;
- повторный рендер UI.

## Почему Это Реализовано Именно Так

В проекте уже сделан правильный ход:
- browser-specific логика живёт только в client-side частях;
- сетевые запросы вынесены в единый API client;
- side effects не размазаны по случайным местам, а собраны в hooks/provider-слое.

Это хороший production-minded подход, потому что:
- код легче читать;
- проще тестировать;
- меньше хаоса между UI и runtime-логикой.

## Какие Anti-Patterns Здесь Нужно Понимать

### Anti-pattern 1. “Я знаю React, значит JavaScript уже не нужен”

Это ошибка.  
Без понимания JavaScript легко:
- путаться в асинхронности;
- ловить странные баги в обработчиках;
- не понимать, почему состояние “устарело”;
- неправильно работать с эффектами.

### Anti-pattern 2. Смешивать UI, сеть и side effects в одном месте

Если обработчик:
- сразу лезет в DOM,
- делает `fetch`,
- меняет 10 кусков состояния,
- пишет в `localStorage`,

то код быстро становится хрупким.

В проекте это уже во многом вынесено в:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts)
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx)

### Anti-pattern 3. Не понимать разницу между синхронным и асинхронным кодом

Тогда разработчик:
- ожидает мгновенного результата от `fetch`;
- забывает `await`;
- ломает UI-логику гонками состояний.

## Что В Этом Проекте Уже Сделано Хорошо

- есть централизованный API client;
- есть осмысленные hooks для чата;
- browser API используются в понятных местах;
- polling и cooldown описаны явно;
- клиентский runtime отделён от server-side частей через `"use client"`.

## Что Ещё Можно Улучшить

1. Отдельно задокументировать browser-only API в клиентских главах.
2. Позже написать отдельную главу про event loop и асинхронность уже глубже, с microtasks/macrotasks.
3. Добавить главу про polling vs WebSockets на frontend и backend сразу в паре.

## Команды

### Проверить версию Node.js

```bash
node --version
```

### Проверить версию npm

```bash
npm --version
```

### Запустить простой JavaScript-файл через Node

```bash
node -e "console.log('hello from javascript runtime')"
```

### Открыть frontend в dev-режиме

```bash
cd apps/frontend
npm run dev
```

## Мини-Упражнения

### Упражнение 1

Откройте:
- [client.ts](c:/dev/portfolio/apps/frontend/src/shared/api/client.ts)
- [useStylistChatSimple.ts](c:/dev/portfolio/apps/frontend/src/features/chat/model/useStylistChatSimple.ts)

И найдите:
- хотя бы одну `async`-функцию;
- хотя бы один `await`;
- хотя бы один `Promise`-ориентированный сценарий.

### Упражнение 2

Откройте:
- [I18nProvider.tsx](c:/dev/portfolio/apps/frontend/src/shared/i18n/I18nProvider.tsx)

И ответьте:
- где здесь работа с `localStorage`;
- где здесь работа с `document.cookie`;
- почему это уже взаимодействие с браузером, а не просто “реакт-код”.

### Упражнение 3

Откройте:
- [ChatWindowSimpleSurface.tsx](c:/dev/portfolio/apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx)

И найдите:
- обработчик `onChange`;
- обработчик `onKeyDown`;
- обработчик `onClick`.

Подумайте, какие именно браузерные события за ними стоят.

## Что Читать Дальше

После этой главы логично идти так:
1. что такое React
2. что такое state, effect и hooks
3. что такое SSR vs SPA
4. что такое FSD-структура фронта
