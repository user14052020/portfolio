# Что Такое package.json В Этом Проекте

Это первая полноценная учебная глава frontend-блока.  
Мы разбираем файл `apps/frontend/package.json` не как “ещё один конфиг”, а как точку, через которую Node.js, npm, Next.js, Docker и сам разработчик понимают, что такое фронтенд-приложение в этом проекте.

## Что Это Академически

`package.json` — это стандартный metadata-файл JavaScript/Node.js-пакета.  
Он описывает пакет, его имя, версию, зависимости, команды запуска и дополнительные свойства, которые нужны инструментам экосистемы Node.

Если говорить строго, `package.json` — это manifest file пакета.

## Что Это Простыми Словами

Если проект на frontend сравнить с цехом, то `package.json` — это его паспорт и краткая инструкция:
- как этот цех называется;
- какие у него есть инструменты;
- какие инструменты нужны для работы, а какие только для сборки и разработки;
- какие команды нужно выполнять, чтобы запустить, собрать и проверить проект.

Без `package.json` npm не понимает:
- что за пакет перед ним;
- что нужно установить;
- какие команды скрываются за `npm run dev`, `npm run build` и `npm run lint`.

## Чем package.json Отличается От Похожих Файлов

### package.json vs package-lock.json

- `package.json` говорит, *какие пакеты нужны в принципе*.
- `package-lock.json` фиксирует, *какие точные версии реально были установлены*.

В этом проекте сейчас есть `package.json`, но в `apps/frontend` нет зафиксированного `package-lock.json`.  
Это означает, что установки зависимостей со временем могут немного различаться. Для production и воспроизводимых сборок это зона улучшения.

## package.json vs tsconfig.json

- `package.json` отвечает за пакет, зависимости и команды.
- `tsconfig.json` отвечает за правила работы TypeScript.

В этом проекте:
- `package.json` хранит `typescript` как инструмент: `apps/frontend/package.json:27-36`
- `tsconfig.json` описывает, как именно TypeScript должен анализировать проект: `apps/frontend/tsconfig.json:2-42`

## package.json vs next.config.mjs

- `package.json` говорит, *какой framework вообще установлен* и *какими командами его запускать*.
- `next.config.mjs` говорит, *как конкретно настроен Next.js*.

В этом проекте:
- Next.js установлен как зависимость: `apps/frontend/package.json:21`
- его runtime-настройки лежат отдельно: `apps/frontend/next.config.mjs:2-13`

## Зачем Это Нужно В Этом Проекте

Для `frontend` нашего проекта `package.json` решает сразу несколько задач:

1. Определяет пакет как отдельную frontend-часть monorepo-подобной структуры.
2. Хранит команды разработки, сборки, запуска и линтинга.
3. Описывает runtime-зависимости UI.
4. Описывает dev-зависимости для TypeScript, ESLint, PostCSS и Tailwind.
5. Используется Dockerfile при сборке контейнера.
6. Является точкой входа для локального запуска фронта.

Без него:
- не сработает `npm install`;
- не сработает `npm run dev`;
- контейнер фронта не сможет установить зависимости;
- Next.js и TypeScript-инструменты не будут правильно подключены.

## Где Это Видно В Коде И Инфраструктуре

### 1. Сам файл package.json

Основной файл:
- `apps/frontend/package.json:1-38`

### 2. Docker использует package.json при сборке

См.:
- `apps/frontend/Dockerfile:5-6`

Там происходит:
- копирование `package.json` и необязательного `package-lock.json`
- запуск `npm install`

Это значит, что Docker-контейнер фронта напрямую зависит от корректности `package.json`.

### 3. README опирается на команды из package.json

См.:
- `README.md:109-111`

Там указано:
- перейти в `apps/frontend`
- выполнить `npm install`
- выполнить `npm run dev`

### 4. Next.js и TypeScript зависят от того, что объявлено в package.json

Связанные файлы:
- `apps/frontend/next.config.mjs:2-13`
- `apps/frontend/tsconfig.json:2-42`

Именно `package.json` говорит системе, что в проекте вообще есть:
- `next`
- `react`
- `react-dom`
- `typescript`
- `eslint`
- `tailwindcss`

## Разбор package.json По Полям

Ниже разбираем файл сверху вниз.

### `name`

См.:
- `apps/frontend/package.json:2`

Значение:
- `"portfolio-frontend"`

Что это значит:
- имя npm-пакета;
- внутреннее имя frontend-модуля;
- его может использовать npm ecosystem и tooling.

В этом проекте это не публичный пакет для публикации в npm, а локальный пакет приложения.

### `version`

См.:
- `apps/frontend/package.json:3`

Значение:
- `"1.0.0"`

Что это значит:
- формальная версия пакета;
- для локального приложения она не так критична, как для библиотеки;
- но она всё равно полезна как marker состояния проекта.

### `private`

См.:
- `apps/frontend/package.json:4`

Значение:
- `true`

Почему это важно:
- npm не даст случайно опубликовать этот пакет в публичный реестр;
- это правильная настройка для внутреннего приложения.

Для продового проекта это хорошая защитная настройка.

### `scripts`

См.:
- `apps/frontend/package.json:5-10`

Это именованные команды, которые запускаются через `npm run <name>`.

#### `dev`

См.:
- `apps/frontend/package.json:6`

Команда:
- `next dev`

Что делает:
- запускает development server Next.js;
- используется локально разработчиком;
- в этом проекте именно эту команду запускает и Docker-контейнер фронта:
  - `apps/frontend/Dockerfile:12`

#### `build`

См.:
- `apps/frontend/package.json:7`

Команда:
- `next build`

Что делает:
- собирает production-бандл Next.js;
- проверяет, что приложение можно собрать;
- генерирует production build-output.

#### `start`

См.:
- `apps/frontend/package.json:8`

Команда:
- `next start`

Что делает:
- запускает уже собранный production-сервер Next.js;
- обычно используется после `npm run build`.

#### `lint`

См.:
- `apps/frontend/package.json:9`

Команда:
- `next lint`

Что делает:
- прогоняет линтер;
- помогает находить проблемный код и нарушения практик.

## Что Такое dependencies

См.:
- `apps/frontend/package.json:11-26`

`dependencies` — это пакеты, которые нужны приложению во время его реальной работы.

Если их не установить:
- фронт не соберётся;
- или соберётся, но не сможет работать корректно.

### Что здесь особенно важно

#### `next`

См.:
- `apps/frontend/package.json:21`

Это framework, на котором построен frontend.  
Он отвечает за:
- маршрутизацию;
- серверный рендеринг;
- клиентские и серверные компоненты;
- сборку приложения.

Связанный файл:
- `apps/frontend/next.config.mjs:2-13`

#### `react` и `react-dom`

См.:
- `apps/frontend/package.json:22-23`

Это ядро UI:
- `react` — модель компонентов и состояния;
- `react-dom` — рендеринг React в браузерную среду.

Связанные файлы:
- `apps/frontend/src/providers/AppProviders.tsx`
- `apps/frontend/src/app/HomePageSurface.tsx`
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`

#### Mantine

См.:
- `apps/frontend/package.json:12-15`

Это UI-библиотека, которая даёт готовые React-компоненты и form/tools.

Примеры использования:
- `apps/frontend/src/providers/AppProviders.tsx`
- `apps/frontend/src/features/contact-request/ui/ContactForm.tsx`
- `apps/frontend/src/widgets/admin/ui/ProjectManager.tsx`

#### `@react-three/fiber` и `@react-three/drei`

См.:
- `apps/frontend/package.json:16-17`

Это зависимости для 3D/scene-слоя на React.

Пример использования:
- `apps/frontend/src/shared/ui/ThreeScenePlaceholder.tsx`

#### `@tabler/icons-react`

См.:
- `apps/frontend/package.json:18`

Это иконки для UI.

Примеры:
- `apps/frontend/src/features/chat/ui/ChatWindowSimpleSurface.tsx`
- `apps/frontend/src/features/chat/ui/UploadArea.tsx`

#### `clsx` и `tailwind-merge`

См.:
- `apps/frontend/package.json:19`
- `apps/frontend/package.json:24`

Они помогают собирать CSS-классы программно.

Пример:
- `apps/frontend/src/shared/lib/cn.ts`

Здесь видно, что:
- `clsx` собирает строки классов;
- `tailwind-merge` убирает конфликтующие Tailwind-классы.

#### `zod`

См.:
- `apps/frontend/package.json:25`

Это библиотека runtime-валидации схем данных.

Важно:
- в текущем frontend-коде она почти не светится;
- это повод позже отдельно проверить, нужна ли она уже сейчас или была добавлена “на вырост”.

#### `framer-motion`

См.:
- `apps/frontend/package.json:20`

Это библиотека для анимаций.

Важно:
- в текущих frontend-файлах её использование почти не видно;
- это тоже отдельная тема для будущего dependency-аудита.

## Что Такое devDependencies

См.:
- `apps/frontend/package.json:27-36`

`devDependencies` — это инструменты, которые нужны разработчику и сборочной среде, но не являются “бизнес-функцией интерфейса” сами по себе.

### Что здесь особенно важно

#### `typescript`

См.:
- `apps/frontend/package.json:36`

Это язык-надстройка для статической типизации.

Связанный файл:
- `apps/frontend/tsconfig.json:2-42`

#### `eslint` и `eslint-config-next`

См.:
- `apps/frontend/package.json:32-33`

Они нужны для проверки качества кода.

#### `tailwindcss`, `postcss`, `autoprefixer`

См.:
- `apps/frontend/package.json:31`
- `apps/frontend/package.json:34-35`

Это инструменты styling-пайплайна.

Связанные файлы:
- `apps/frontend/tailwind.config.ts`
- `apps/frontend/postcss.config.js`
- `apps/frontend/src/app/globals.css`

#### `@types/node`, `@types/react`, `@types/react-dom`

См.:
- `apps/frontend/package.json:28-30`

Это type definitions, которые помогают TypeScript понимать API соответствующих библиотек.

## Как package.json Влияет На Реальный Запуск Проекта

Путь запуска выглядит так:

1. Разработчик заходит в `apps/frontend`.
2. Выполняет `npm install`.
3. npm читает `package.json`.
4. npm устанавливает пакеты из `dependencies` и `devDependencies`.
5. Разработчик запускает `npm run dev`.
6. npm смотрит в `scripts.dev`.
7. Запускается `next dev`.
8. Next.js читает `next.config.mjs`.
9. TypeScript-инструменты читают `tsconfig.json`.
10. После этого frontend начинает отвечать на `3000` порту.

То же самое происходит и в Docker-контейнере, только команды выполняет уже не человек, а Dockerfile.

## Какие Команды Здесь Нужно Знать

### Локальная установка и запуск

```bash
cd apps/frontend
npm install
npm run dev
```

См.:
- `README.md:109-111`

### Production-сборка

```bash
cd apps/frontend
npm run build
npm run start
```

### Проверка линтера

```bash
cd apps/frontend
npm run lint
```

### Посмотреть, установлена ли конкретная зависимость

```bash
cd apps/frontend
npm ls next react typescript
```

## Какие Anti-Patterns Здесь Нужно Понимать

### Anti-pattern 1. Считать, что package.json — это просто “список библиотек”

Нет.  
Это ещё и:
- набор команд;
- описание роли пакета;
- точка входа для npm;
- важный элемент Docker-сборки.

### Anti-pattern 2. Не различать dependencies и devDependencies

Если положить пакет не туда:
- сборка может вести себя странно;
- runtime-зависимость может отсутствовать там, где нужна;
- production image может получиться тяжелее, чем надо.

### Anti-pattern 3. Не фиксировать lockfile

Если нет `package-lock.json`, установки со временем могут дрейфовать.  
Для production-проекта это ощутимый риск воспроизводимости.

## Что В Этом Проекте Уже Сделано Хорошо

- frontend выделен в отдельный пакет;
- пакет помечен как `private`;
- есть понятные `scripts`;
- зависимости разделены на runtime и dev;
- Dockerfile опирается на manifest корректно;
- Next.js, TypeScript и Tailwind выделены в явные части toolchain.

## Что Ещё Можно Улучшить

1. Зафиксировать `package-lock.json`, чтобы сборки были воспроизводимее.
2. Периодически делать audit зависимостей.
3. Проверить, какие пакеты реально используются, а какие были добавлены “на вырост”.
4. Позже можно формализовать policy обновления версий библиотек.

## Мини-Упражнения

### Упражнение 1

Откройте `apps/frontend/package.json` и найдите:
- имя пакета;
- команды запуска;
- основной framework;
- библиотеку типизации;
- библиотеку для Tailwind merge.

### Упражнение 2

Ответьте письменно:
- почему `private: true` полезен;
- чем `dependencies` отличаются от `devDependencies`;
- почему `npm run dev` не может сработать, если нет блока `scripts`.

### Упражнение 3

Сопоставьте файлы:
- `package.json`
- `Dockerfile`
- `next.config.mjs`
- `tsconfig.json`

И объясните, кто из них отвечает:
- за установку пакетов;
- за команды запуска;
- за настройку Next.js;
- за настройку TypeScript.

## Что Читать Дальше

После этой главы логично идти в таком порядке:
1. `tsconfig.json`
2. `next.config.mjs`
3. что такое React
4. что такое FSD-структура фронта
