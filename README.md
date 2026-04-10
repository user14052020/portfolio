
# Portfolio — сайт-портфолио

Мой персональный сайт-портфолио, в котором собраны демо-проекты, блог и административная панель.  
Проект построен как fullstack-монорепозиторий: **Next.js frontend + FastAPI backend**.

Ключевая демонстрационная функция — **AI-стилист**: пользователь может общаться с ботом как со стилистом, отправлять текст и изображения, получать советы по сочетанию одежды и генерировать **flat lay** референс-изображения образов.

[Учебник по программированию на базе этого проекта](./docs/academy/README.md)

---

## Что умеет проект

- показывать мои проекты в виде визуальных карточек;
- вести блог с постами;
- поддерживать двуязычный интерфейс;
- иметь административную панель для управления контентом;
- обрабатывать загрузку файлов;
- хранить и искать данные по проектам, постам и заявкам;
- запускать AI-сценарии стилиста с генерацией изображений.

---

## AI-стилист

Один из главных модулей проекта — чат-бот стилиста.

### Что он делает

- принимает **текст** и **изображения** от пользователя;
- подсказывает, **с чем носить вещь**;
- предлагает **образ на мероприятие**;
- показывает **случайный стиль**;
- генерирует **flat lay** референс-изображение образа.

### Как устроен

В локальной конфигурации AI-стилист работает через связку:

- **vLLM** — текстовая reasoning / chat часть;
- **ComfyUI** — генерация flat lay изображений;
- **FastAPI backend** — orchestration, API, jobs, сохранение состояния;
- **Next.js frontend** — UI чата и отображение результата.

### База стилей

База стилей наполняется отдельным **парсером**, который собирает данные из API сайтов-доноров, нормализует их и сохраняет в БД.  
Это нужно для того, чтобы бот:

- лучше различал стили;
- давал более осмысленные советы;
- генерировал более разнообразные образы;
- в будущем опирался не только на LLM, но и на собственную knowledge base.

---

## Технологический стек

### Backend
- FastAPI
- async SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Elasticsearch
- JWT auth
- RBAC

### Frontend
- Next.js 14
- React 18
- Mantine
- Tailwind CSS
- TypeScript
- FSD-oriented structure

### AI / Infra
- vLLM
- ComfyUI
- Docker Compose

---

## Структура репозитория

```text
.
├── apps
│   ├── backend
│   └── frontend
├── docs
├── media
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## Быстрый старт через Docker

### 1. Скопировать переменные окружения

```bash
cp .env.example .env
```

### 2. Запустить проект

```bash
docker compose up --build -d
```

### 3. Применить миграции

```bash
docker compose exec backend alembic upgrade head
```

### 4. Выполнить сидирование

```bash
docker compose exec backend python scripts/seed.py
```

### 5. Открыть проект

- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`

---

## Что важно настроить в `.env`

Минимум проверь эти поля:

- `SECRET_KEY`
- `INITIAL_ADMIN_EMAIL`
- `INITIAL_ADMIN_PASSWORD`
- `COMFYUI_BASE_URL`
- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_MEDIA_URL`
- `NEXT_PUBLIC_SITE_URL`

Если backend и frontend запускаются в Docker, также проверь:

- `INTERNAL_API_URL`

---

## Локальный запуск без Docker

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
---

## Установка vLLM и ComfyUI

[Инструкция по установке vLLM и ComfyUI](./docs/vllm-comfyui/how-install-vllm-comfyui/README.md)

---

## Запуск vLLM

Ниже пример локального запуска vLLM для AI-стилиста.  
Подставь свою модель, порт и лимит VRAM при необходимости.

```bash
python -m vllm.entrypoints.openai.api_server   --model Qwen/Qwen2.5-3B-Instruct   --host 0.0.0.0   --port 8001   --max-model-len 4096   --gpu-memory-utilization 0.6
```

Если ты запускаешь vLLM в отдельной Linux/WSL-среде, backend должен видеть этот endpoint по сети.

---

## Запуск ComfyUI

Пример обычного серверного запуска ComfyUI:

```bash
python main.py   --listen 0.0.0.0   --port 8188   --disable-auto-launch   --preview-method none
```

Backend использует workflow для fashion flat lay и отправляет generation jobs в ComfyUI по HTTP API.

---

## Связка backend ↔ vLLM ↔ ComfyUI

Типовая локальная схема:

- **frontend** → общается только с backend;
- **backend** → общается с vLLM;
- **backend** → отправляет generation jobs в ComfyUI;
- **ComfyUI** → возвращает статус и результат генерации.

Это упрощает архитектуру и не раскрывает AI-сервисы напрямую в UI.

---

## Админ-панель

После сидирования создаётся администратор из `.env`:

- Email: `INITIAL_ADMIN_EMAIL`
- Password: `INITIAL_ADMIN_PASSWORD`

Через admin UI можно управлять:
- проектами,
- постами,
- настройками,
- заявками,
- generation jobs.

---

## Поиск и медиа

### Поиск
Используется Elasticsearch.  
Если поисковый движок временно недоступен, list endpoints продолжают работать через БД.

### Медиа
Файлы хранятся локально в `./media`, backend раздаёт их через `/media`.  
Эта часть изолирована и может быть заменена позже на S3-совместимое хранилище.

---

## Что проект демонстрирует

Этот репозиторий показывает мой подход к разработке:

- fullstack-архитектура;
- модульная организация кода;
- работа с асинхронным backend;
- AI-интеграции;
- генерация изображений;
- подготовка проекта к дальнейшему масштабированию.


