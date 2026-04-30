import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.integrations.elasticsearch import close_elasticsearch_client
from app.db.session import SessionLocal
from app.services.admin_bootstrap import configured_admin_bootstrap_service
from app.services.search import search_service
from app.services.style_ingestion_admin import style_ingestion_admin_service
from app.tasks.chat_retention_cleanup import run_chat_retention_cleanup
from app.tasks.generation_polling import run_generation_job_poller


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    poller_stop_event = asyncio.Event()
    retention_stop_event = asyncio.Event()
    poller_task: asyncio.Task[None] | None = None
    retention_task: asyncio.Task[None] | None = None

    settings.media_root.mkdir(parents=True, exist_ok=True)
    async with SessionLocal() as session:
        await configured_admin_bootstrap_service.ensure_configured_admin(session)
    await search_service.ensure_indices()
    if settings.enable_generation_job_poller:
        poller_task = asyncio.create_task(run_generation_job_poller(poller_stop_event))
    if settings.enable_chat_retention_cleanup:
        retention_task = asyncio.create_task(run_chat_retention_cleanup(retention_stop_event))
    yield
    poller_stop_event.set()
    retention_stop_event.set()
    if poller_task is not None:
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
    if retention_task is not None:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
    style_ingestion_admin_service.shutdown()
    await close_elasticsearch_client()


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(settings.media_url, StaticFiles(directory=settings.media_root), name="media")
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
