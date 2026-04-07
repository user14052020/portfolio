# Academy Term Coverage Checklist

Этот файл нужен как контроль покрытия всего обязательного стека и всех обязательных терминов.

Логика простая:
- курс идёт от основ программирования к текущему проекту;
- параллельно мы сверяемся с этим чеклистом;
- галочку ставим только тогда, когда тема реально закрыта отдельной главой или набором глав;
- если термин можно частично объяснить раньше, мы это делаем, но не считаем тему полностью закрытой раньше времени.

## Обязательное Правило Для Каждого Пункта

Для каждого термина из этого чеклиста в учебнике обязательно должны быть:
- академическое определение;
- объяснение простыми словами;
- отличие от соседних понятий;
- практический пример;
- пример из текущего проекта, если он есть;
- простой вымышленный пример, если в проекте такого кейса нет;
- ссылки на файлы, функции, классы, роуты или конфиги;
- хотя бы одна команда или упражнение.

## Чеклист Покрытия

### Backend, API, архитектура

- [x] Python
- [ ] Django
- [ ] REST API
- [ ] GraphQL
- [ ] Microservices architecture
- [ ] SaaS-продукт
- [ ] LMS-платформа
- [ ] Принципы чистой архитектуры
- [ ] Принципы масштабируемых систем
- [ ] Принципы ООП
- [ ] Принципы SOLID

### Frontend

- [x] JavaScript
- [ ] React
- [ ] Next.js
- [x] TypeScript
- [ ] SSR архитектура
- [ ] SPA архитектура

### Data and infrastructure

- [x] PostgreSQL
- [x] Redis
- [ ] Docker
- [ ] Git
- [ ] CI/CD pipelines
- [ ] Nginx
- [ ] WebSockets
- [ ] Real-time features
- [ ] Cloud infrastructure
- [ ] AWS
- [ ] GCP
- [ ] DigitalOcean
- [ ] CDN integration

## Что Уже Частично Покрыто, Но Пока Не Закрыто

Поддерживающие материалы уже есть, но полную галочку по этим темам пока не ставим:
- Next.js: есть главы про `next.config.mjs` и часть runtime-поведения;
- browser runtime и vanilla JavaScript: уже есть полноценная базовая глава, но это ещё не закрывает React/Next.js целиком.

## Текущий Прогресс По Ходу Курса

### Foundations

- [x] Что такое компьютерная программа
- [x] Что такое файл, каталог и проект
- [x] Что такое процесс, память и ОС
- [x] Что такое язык программирования
- [x] Что такое package manager и зависимости
- [x] Что такое API и HTTP
- [x] Что такое база данных
- [x] SQL vs NoSQL
- [x] Кэш и поиск
- [ ] OOP, SOLID и clean architecture
- [ ] Modular monolith vs microservices
- [ ] REST vs GraphQL
- [ ] SaaS-продукт и LMS-платформа
- [ ] Масштабируемая система

## Что Уже Написано И Точно Работает Как Опора

- [00-roadmap.md](./00-roadmap.md)
- [01-writing-standard.md](./01-writing-standard.md)
- [03-industry-stack-and-requirements-map.md](./03-industry-stack-and-requirements-map.md)
- [foundations/09-what-is-a-database.md](./foundations/09-what-is-a-database.md)
- [foundations/10-sql-vs-nosql.md](./foundations/10-sql-vs-nosql.md)
- [foundations/11-what-is-cache-and-search.md](./foundations/11-what-is-cache-and-search.md)
- [frontend/04-package-json-deep-dive.md](./frontend/04-package-json-deep-dive.md)
- [frontend/05-tsconfig-deep-dive.md](./frontend/05-tsconfig-deep-dive.md)
- [frontend/06-next-config-deep-dive.md](./frontend/06-next-config-deep-dive.md)
- [frontend/07-vanilla-javascript-browser-runtime.md](./frontend/07-vanilla-javascript-browser-runtime.md)

## Принцип Закрытия Темы

Тема считается закрытой только если выполнены все условия:

1. Есть отдельная глава или явный раздел в полноценной главе.
2. Есть определение.
3. Есть объяснение простыми словами.
4. Есть пример из проекта или явно помеченный вымышленный пример.
5. Есть практический блок: команда, упражнение или мини-разбор.

Если выполнено только часть условий, галочка не ставится.
