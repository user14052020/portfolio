from fastapi import APIRouter

from app.api.routes import (
    auth,
    blog_posts,
    contact_requests,
    generation_jobs,
    projects,
    site_settings,
    style_ingestion_admin,
    style_ingestion_settings,
    stylist_runtime_settings,
    stylist_chat,
    uploads,
    users,
)


api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(projects.router)
api_router.include_router(blog_posts.router)
api_router.include_router(contact_requests.router)
api_router.include_router(site_settings.router)
api_router.include_router(style_ingestion_admin.router)
api_router.include_router(style_ingestion_settings.router)
api_router.include_router(stylist_runtime_settings.router)
api_router.include_router(uploads.router)
api_router.include_router(stylist_chat.router)
api_router.include_router(generation_jobs.router)
