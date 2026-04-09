# Portfolio AI Stylist Monorepo

Production-oriented starter monorepo for a bilingual `ru/en` portfolio website with:

- FastAPI backend with async SQLAlchemy, Alembic, PostgreSQL, Redis, Elasticsearch, JWT auth and RBAC.
- Next.js frontend with Mantine, Tailwind CSS, FSD-oriented structure, instant locale switch and admin UI.
- AI stylist chat flow with upload support and generation jobs routed to local-network ComfyUI.
- Docker Compose infrastructure for local development.

## Repository layout

```text
.
├── apps
│   ├── backend
│   └── frontend
├── media
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Main capabilities

- Bilingual portfolio pages with runtime locale switching.
- Portfolio projects rendered as creative app-window cards.
- Blog with text/video post support, search and filtering.
- Contact modal and request management.
- Protected admin area for projects, posts, settings, contacts and generation jobs.
- 3D scene placeholders wired for React Three Fiber on each page.
- Generation provider abstraction with ComfyUI implementation and polling-based status tracking.

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ for local frontend development without Docker
- Python 3.12+ for local backend development without Docker
- A local-network machine running ComfyUI HTTP API

## Environment

1. Copy the example file:

```bash
cp .env.example .env
```

2. Update at least:

- `SECRET_KEY`
- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`
- `COMFYUI_BASE_URL`
- `INTERNAL_API_URL` if frontend runs in Docker and server-side Next.js requests should target the backend service name
- `DATABASE_URL`, `SYNC_DATABASE_URL`, `REDIS_URL`, `ELASTICSEARCH_URL` only if you intentionally change Docker service names or move these dependencies outside Compose

## Running with Docker

1. Build and start services:

```bash
docker compose up --build
```

2. Apply migrations:

```bash
docker compose exec backend alembic upgrade head
```

3. Seed initial data:

```bash
docker compose exec backend python scripts/seed.py
```

`seed.py` поднимает только стартовые данные приложения и администратора.
Он не наполняет style-каталог parser-а, не импортирует legacy `txt`-списки стилей и не связан с style ingestion.
Style ingestion живёт отдельно и для `aesthetics_wiki` теперь запускается только по API-first пути.

Run the commands above one by one. If you want the terminal back immediately, use detached mode:

```bash
docker compose up --build -d
```

4. Open:

- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8000/docs`

PostgreSQL, Redis and Elasticsearch are internal-only in the default Compose setup. The backend reaches them over the Docker network via `postgres:5432`, `redis:6379` and `elasticsearch:9200`, so they do not consume host ports unless you explicitly publish them.

## Style ingestion

Основной путь для parser-а сейчас такой:

1. Поставить style pages в API job queue:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode enqueue-jobs --limit 50"
```

2. Обработать очередь штатным worker-ом:

```bash
docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh --mode run-worker --worker-max-jobs 50 --worker-stop-when-idle"
```

Что важно:

- `enqueue-jobs` делает discovery через `MediaWiki Action API`
- detail fetch тоже идёт через `MediaWiki Action API`
- если у страницы уже сохранена та же `revision_id`, новый detail fetch не ставится
- retryable fetch-ошибки worker сам requeue-ит с backoff

Полный операционный runbook лежит в [docs/upd/style_ingestion_operations.md](./docs/upd/style_ingestion_operations.md).

## Running locally without Docker

### Backend

```bash
cd apps/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export $(grep -v '^#' ../../.env | xargs)
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload
```

### Frontend

```bash
cd apps/frontend
npm install
npm run dev
```

## Default admin credentials

The seed script creates the admin defined in `.env`:

- Email: `INITIAL_ADMIN_EMAIL`
- Password: `INITIAL_ADMIN_PASSWORD`

## ComfyUI integration

The backend uses a provider abstraction. Today it ships with:

- `ComfyUIClient` for queueing prompt payloads and polling generation status.
- `GenerationService` for provider orchestration, persistence and result hydration.
- `StylistService` mock recommendation layer that can later be replaced by an LLM or rules engine.

Set `COMFYUI_BASE_URL` to the machine on your local network running ComfyUI. The sample workflow template is stored in `apps/backend/app/integrations/workflows/fashion_flatlay.json`.

## Search

Elasticsearch is used through a thin abstraction. If Elasticsearch is temporarily unavailable, list endpoints still fall back to database queries. Search indexing is best-effort and non-blocking by design.

## Media storage

- Uploaded files are stored locally in `./media`
- Backend serves them via `/media`
- The storage adapter is intentionally isolated so it can be swapped for S3-compatible storage later

## What is included

- Base Dockerfiles and Compose stack
- Alembic setup and initial migration
- Seed script with starter content
- REST API for auth, projects, blog posts, uploads, contact requests, settings, stylist chat and generation jobs
- Modern frontend scaffold with reusable windowed UI, chat section and admin workspace

## What to harden before production

- Replace local media storage with S3-compatible storage and CDN.
- Move JWT handling to secure HTTP-only cookies.
- Add background worker queue for generation polling and indexing.
- Add real LLM-powered stylist recommendations.
- Add server-side admin route protection and audit logging.
- Add observability, rate limiting, backups and CI/CD pipelines.
