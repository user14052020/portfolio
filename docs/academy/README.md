# Project Academy

Этот раздел `docs/academy` — каркас будущего мини-учебника по проекту `portfolio`.

Цель:
- объяснить проект так, чтобы начинающий разработчик понял не только `что здесь лежит`, но и `почему это вообще существует`;
- пройти путь от базовых академических определений до реальных файлов и функций в этом репозитории;
- разложить `frontend`, `backend`, инфраструктуру и интеграции по понятным учебным модулям;
- в конце дойти до связи кода с рантаймом, процессами, сетью, базой данных и операционной системой.

Этот раздел намеренно строится как курс, а не как сухой reference.

Структура:
- [00-roadmap.md](./00-roadmap.md) — общий учебный маршрут.
- [01-writing-standard.md](./01-writing-standard.md) — единый шаблон для всех будущих глав.
- [02-project-file-atlas.md](./02-project-file-atlas.md) — общий план полного разбора файлов проекта.
- [03-industry-stack-and-requirements-map.md](./03-industry-stack-and-requirements-map.md) — карта внешнего стека, инженерных требований и сравнительных тем, которые тоже должны быть покрыты курсом.
- [04-term-coverage-checklist.md](./04-term-coverage-checklist.md) — чеклист обязательных терминов и тем с галочками закрытия.
- [foundations/01-foundations-roadmap.md](./foundations/01-foundations-roadmap.md) — основы программирования, рантаймов и связи с ОС.
- [foundations/02-foundations-glossary-plan.md](./foundations/02-foundations-glossary-plan.md) — словарь базовых терминов.
- [foundations/03-what-is-a-program.md](./foundations/03-what-is-a-program.md) — первая фундаментальная глава про то, что такое программа и как она проявляется в этом проекте.
- [foundations/04-what-is-a-file-directory-project.md](./foundations/04-what-is-a-file-directory-project.md) — глава про файл, каталог, проект, дерево репозитория и абсолютные/относительные пути.
- [foundations/05-what-is-a-process-memory-os.md](./foundations/05-what-is-a-process-memory-os.md) — глава про процесс, поток, память, ОС, сокеты, порты, environment и то, как все это проявляется в runtime этого проекта.
- [foundations/06-what-is-a-programming-language.md](./foundations/06-what-is-a-programming-language.md) — глава про язык программирования, синтаксис, runtime, стандартную библиотеку и роли `JavaScript`, `TypeScript` и `Python` в этом проекте.
- [foundations/07-what-is-a-package-manager-and-dependencies.md](./foundations/07-what-is-a-package-manager-and-dependencies.md) — глава про package manager, зависимости, `npm`, `pip`, `package.json`, `requirements.txt`, lock files и semver на примере этого проекта.
- [foundations/08-what-is-api-and-http.md](./foundations/08-what-is-api-and-http.md) — глава про `API`, `HTTP`, `request`, `response`, `method`, `headers`, `status code`, `JSON` и реальные endpoints проекта.
- [foundations/09-what-is-a-database.md](./foundations/09-what-is-a-database.md) — глава про базу данных, таблицы, строки, колонки, индексы, транзакции, миграции и связь этого слоя с PostgreSQL в текущем проекте.
- [foundations/10-sql-vs-nosql.md](./foundations/10-sql-vs-nosql.md) — глава про `SQL`, `NoSQL`, `PostgreSQL`, `MongoDB`, таблицы против документов и причины, по которым этот проект опирается именно на реляционную модель.
- [foundations/11-what-is-cache-and-search.md](./foundations/11-what-is-cache-and-search.md) — глава про `cache`, `Redis`, `TTL`, полнотекстовый поиск, `Elasticsearch` и разделение ролей между базой, кэшем и поисковым индексом в этом проекте.
- [infrastructure/01-infra-roadmap.md](./infrastructure/01-infra-roadmap.md) — Docker, Postgres, Redis, Elasticsearch, vLLM, ComfyUI, миграции.
- [infrastructure/02-runtime-and-ops-atlas-plan.md](./infrastructure/02-runtime-and-ops-atlas-plan.md) — карта runtime и operational-файлов.
- [frontend/01-frontend-roadmap.md](./frontend/01-frontend-roadmap.md) — учебный план по клиентской части.
- [frontend/04-package-json-deep-dive.md](./frontend/04-package-json-deep-dive.md) — первая полноценная глава про `package.json`, npm-скрипты, зависимости и связь фронта с Node/Next/Docker.
- [frontend/05-tsconfig-deep-dive.md](./frontend/05-tsconfig-deep-dive.md) — подробная глава про `tsconfig.json`, строгую типизацию, JSX, алиасы `@/` и интеграцию TypeScript с Next.js.
- [frontend/06-next-config-deep-dive.md](./frontend/06-next-config-deep-dive.md) — подробная глава про `next.config.mjs`, strict mode, distDir и image policy.
- [frontend/07-vanilla-javascript-browser-runtime.md](./frontend/07-vanilla-javascript-browser-runtime.md) — глава про vanilla JavaScript, browser runtime, DOM, события, `Promise`, `async/await`, `fetch` и event loop.
- [frontend/02-frontend-file-atlas-plan.md](./frontend/02-frontend-file-atlas-plan.md) — карта frontend-файлов.
- [frontend/03-frontend-architecture-and-improvements-plan.md](./frontend/03-frontend-architecture-and-improvements-plan.md) — FSD, Tailwind CSS, vanilla JS база и будущие улучшения фронта.
- [backend/01-backend-roadmap.md](./backend/01-backend-roadmap.md) — учебный план по серверной части.
- [backend/02-backend-file-atlas-plan.md](./backend/02-backend-file-atlas-plan.md) — карта backend-файлов.
- [backend/03-backend-production-patterns-plan.md](./backend/03-backend-production-patterns-plan.md) — продовые backend-паттерны, зоны роста и anti-patterns.

Как мы будем заполнять этот курс:
1. Сначала создаём полную карту тем и файлов.
2. Затем берём один блок за раз и пишем подробную главу.
3. В каждой главе идём от академического определения к простому объяснению.
4. После этого показываем конкретные примеры в коде проекта.
5. В конце главы даём команды, упражнения и идеи для самостоятельных изменений.

Ожидаемый формат каждой будущей главы:
1. Академическое определение термина.
2. Объяснение простыми словами.
3. Зачем это нужно именно в этом проекте.
4. Где это лежит в коде.
5. Разбор конкретных функций, классов, маршрутов или конфигов.
6. Практические команды.
7. Маленькие упражнения.

Важно:
- здесь будут не только главы `что такое React/FastAPI/Postgres`, но и главы `что такое файл package.json`, `что такое миграция`, `что делает docker-compose.yml`, `как код превращается в HTTP-ответ`, `как запрос доходит до базы`, `как задача генерации живёт в рантайме`;
- MongoDB будет разобран как сравнительная тема, даже если в проекте он не используется;
- на следующих итерациях мы добавим ссылки не только на файлы, но и на конкретные строки и функции.
