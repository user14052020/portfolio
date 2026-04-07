# Industry Stack And Requirements Map

Этот файл нужен, чтобы учебный контур учитывал не только текущую реализацию `portfolio`, но и более широкий набор технологий и инженерных требований, которые часто встречаются в вакансиях и production-командах.

Важно: часть тем уже реализована в проекте напрямую, а часть должна быть разобрана как сравнительный материал.

## Что уже реализовано напрямую

### Backend and data

- Python backend
- REST API
- PostgreSQL
- Redis
- Elasticsearch
- async database access

### Frontend

- React
- Next.js
- TypeScript
- SSR/CSR hybrid model Next.js
- Tailwind CSS
- FSD-oriented structure

### Runtime and operations

- Docker
- Git-based workflow
- локальная runtime-топология с Windows host, WSL и Ubuntu VM

## Что нужно покрыть как сравнительные темы

### Django

Нужно отдельно разобрать:
- чем Django отличается от FastAPI;
- когда Django был бы хорошим выбором;
- что значит “batteries included” framework.

### GraphQL

Нужно отдельно разобрать:
- чем GraphQL отличается от REST;
- какие у него сильные стороны;
- почему текущий проект использует REST.

### Microservices architecture

Нужно отдельно разобрать:
- что такое микросервисы;
- чем microservices отличаются от modular monolith;
- почему разделение по папкам и интеграциям ещё не делает систему микросервисной автоматически.

### SSR / SPA architecture

Нужно отдельно разобрать:
- что такое SSR;
- что такое SPA;
- что такое CSR;
- как Next.js сочетает эти режимы.

### WebSockets / Real-time features

Нужно отдельно разобрать:
- что такое real-time transport;
- когда хватает polling;
- когда нужны WebSockets;
- почему сейчас generation-status идёт через polling.

### Nginx

Нужно отдельно разобрать:
- что такое reverse proxy;
- зачем Nginx ставят перед backend/frontend;
- как он связан с SSL, static files и routing.

### Cloud infrastructure and CDN

Нужно отдельно разобрать:
- AWS / GCP / DigitalOcean как типовые платформы развертывания;
- что такое CDN;
- зачем CDN нужен для статики и media.

### SaaS product

Нужно отдельно разобрать:
- что такое SaaS-продукт;
- чем SaaS отличается от обычного сайта;
- как роли, админка, API, фоновые задачи и интеграции связаны с SaaS-мышлением.

### LMS platform

Нужно отдельно разобрать:
- что такое LMS;
- какие сущности там обычно центральные: пользователь, курс, урок, прогресс, уведомления;
- как знания из этого проекта переносятся на LMS-платформу.

### Git / CI/CD pipelines

Нужно отдельно разобрать:
- что Git делает в инженерном процессе;
- что такое pipeline;
- как код проходит путь от commit до деплоя.

## Что нужно покрыть как инженерные требования

### Clean architecture

Нужно отдельно разобрать:
- границы слоёв;
- направленность зависимостей;
- почему это важно для масштабируемых систем.

### OOP

Нужно отдельно разобрать:
- класс;
- объект;
- композицию;
- инкапсуляцию;
- когда ООП помогает, а когда только усложняет проект.

### SOLID

Нужно разобрать:
- SRP
- OCP
- LSP
- ISP
- DIP

И обязательно показывать:
- где это видно в проекте;
- где пока есть зоны роста.

### SaaS / platform thinking

Нужно отдельно объяснить:
- чем продуктовая платформа отличается от набора страниц;
- что дают versioned API, admin area, generation jobs и healthcheck;
- как такие подходы переносятся на LMS и другие SaaS-платформы.

### Scalable systems

Нужно отдельно разобрать:
- что такое масштабируемая система;
- чем vertical scaling отличается от horizontal scaling;
- почему кэш, очереди, healthcheck, декомпозиция и идемпотентность важны под рост нагрузки;
- где в текущем проекте уже есть элементы такого мышления.

## Куда это раскладывается в academy

- Foundations: OOP, SOLID, clean architecture, REST vs GraphQL, modular monolith vs microservices, SaaS, LMS, scalable systems
- Frontend: SSR vs SPA, FSD, Tailwind, browser runtime, real-time UI patterns
- Backend: Python/FastAPI, Django as comparison, REST API design, layered architecture
- Infrastructure: Docker, Git, CI/CD, Nginx, cloud deployment, CDN, WebSockets vs polling
