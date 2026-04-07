# Foundations Roadmap

Этот блок нужен, чтобы дойти `до атома` и понять, что вообще такое программирование и как код связан с операционной системой.

## Главы, которые нужно написать

### 01. Что такое компьютерная программа

Разобрать:
- инструкция;
- данные;
- вход и выход;
- алгоритм;
- состояние.

Отдельная глава:
- [03-what-is-a-program.md](./03-what-is-a-program.md)

### 02. Что такое файл, каталог и проект

Разобрать:
- файл;
- расширение;
- папка;
- дерево проекта;
- путь;
- абсолютный и относительный путь.

Отдельная глава:
- [04-what-is-a-file-directory-project.md](./04-what-is-a-file-directory-project.md)

### 03. Что такое процесс, память и ОС

Разобрать:
- процесс;
- поток;
- память;
- дескрипторы;
- сеть;
- сокеты;
- переменные окружения;
- права доступа.

Отдельная глава:
- [05-what-is-a-process-memory-os.md](./05-what-is-a-process-memory-os.md)

### 04. Что такое язык программирования

Разобрать:
- JavaScript;
- TypeScript;
- Python;
- что такое синтаксис;
- что такое runtime;
- что такое стандартная библиотека.

Отдельная глава:
- [06-what-is-a-programming-language.md](./06-what-is-a-programming-language.md)

### 05. Что такое package manager и зависимости

Разобрать:
- `npm`;
- `pip`;
- `requirements.txt`;
- `package.json`;
- lock-файлы;
- версия пакета;
- semver.

Отдельная глава:
- [07-what-is-a-package-manager-and-dependencies.md](./07-what-is-a-package-manager-and-dependencies.md)

### 06. Что такое API и HTTP

Разобрать:
- клиент;
- сервер;
- HTTP;
- JSON;
- request;
- response;
- method;
- headers;
- status code.

Отдельная глава:
- [08-what-is-api-and-http.md](./08-what-is-api-and-http.md)

### 07. Что такое база данных

Разобрать:
- таблица;
- строка;
- колонка;
- индекс;
- запрос;
- транзакция;
- миграция.

Отдельная глава:
- [09-what-is-a-database.md](./09-what-is-a-database.md)

### 08. SQL vs NoSQL

Разобрать:
- SQL;
- PostgreSQL;
- MongoDB;
- когда выбирают таблицы;
- когда выбирают документы;
- почему в нашем проекте выбран Postgres.

Отдельная глава:
- [10-sql-vs-nosql.md](./10-sql-vs-nosql.md)

### 09. Кэш и поиск

Разобрать:
- Redis;
- Elasticsearch;
- чем кэш отличается от базы;
- чем полнотекстовый поиск отличается от обычного SQL-запроса.

Отдельная глава:
- [11-what-is-cache-and-search.md](./11-what-is-cache-and-search.md)

### 10. Что такое OOP, SOLID и clean architecture

Разобрать:
- класс;
- объект;
- композиция;
- инкапсуляция;
- ответственность;
- SOLID;
- границы слоёв;
- направленность зависимостей;
- чистую архитектуру как инженерное мышление.

### 11. Modular monolith vs microservices

Разобрать:
- что такое монолит;
- что такое modular monolith;
- что такое microservices;
- почему разделение по модулям и runtime-компонентам не делает систему микросервисной автоматически.

### 12. REST vs GraphQL

Разобрать:
- что такое REST;
- что такое GraphQL;
- когда REST проще и надёжнее;
- когда GraphQL оправдан.

### 13. Что такое SaaS-продукт и LMS-платформа

Разобрать:
- что такое SaaS;
- чем SaaS отличается от обычного сайта;
- что такое LMS;
- какие типичные модули есть у LMS;
- как идеи этого проекта переносятся в SaaS и LMS.

### 14. Что такое масштабируемая система

Разобрать:
- что такое масштабируемость;
- что такое отказоустойчивость;
- vertical vs horizontal scaling;
- зачем нужны кэш, фоновые задачи, декомпозиция и контроль границ;
- почему масштабируемость нельзя свести только к "поставить сервер мощнее".

## На что потом будем ссылаться из проекта

### Фронтенд

- `apps/frontend/package.json`
- `apps/frontend/tsconfig.json`
- `apps/frontend/src/shared/api/client.ts`
- `apps/frontend/src/app/page.tsx`

### Бекенд

- `apps/backend/requirements.txt`
- `apps/backend/app/main.py`
- `apps/backend/app/db/session.py`
- `apps/backend/alembic/env.py`

### Инфраструктура

- `docker-compose.yml`
- `.env.example`
- `docs/06-autostart-map.md`
- `docs/07-vllm-runtime-reference.md`
- `docs/08-comfyui-runtime-reference.md`

## Результат блока

После завершения этого блока читатель должен понимать:
- что такое программа;
- как код запускается;
- как код общается по сети;
- почему нужны базы, кэш, миграции и контейнеры;
- чем этот проект как система отличается от `просто набора файлов`.

## Связанный план

- [02-foundations-glossary-plan.md](./02-foundations-glossary-plan.md) — подробная карта терминов, которые будут раскрываться в этом блоке.
