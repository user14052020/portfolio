from typing import Any

from elasticsearch import NotFoundError

from app.integrations.elasticsearch import get_elasticsearch_client
from app.models import BlogPost, Project


class SearchService:
    async def ensure_indices(self) -> None:
        client = get_elasticsearch_client()
        if client is None:
            return

        project_mapping = {
            "mappings": {
                "properties": {
                    "slug": {"type": "keyword"},
                    "title_ru": {"type": "text"},
                    "title_en": {"type": "text"},
                    "summary_ru": {"type": "text"},
                    "summary_en": {"type": "text"},
                    "stack": {"type": "keyword"},
                }
            }
        }
        blog_mapping = {
            "mappings": {
                "properties": {
                    "slug": {"type": "keyword"},
                    "title_ru": {"type": "text"},
                    "title_en": {"type": "text"},
                    "excerpt_ru": {"type": "text"},
                    "excerpt_en": {"type": "text"},
                    "tags": {"type": "keyword"},
                }
            }
        }

        try:
            if not await client.indices.exists(index="projects"):
                await client.indices.create(index="projects", **project_mapping)
            if not await client.indices.exists(index="blog_posts"):
                await client.indices.create(index="blog_posts", **blog_mapping)
        except Exception:
            return

    async def index_project(self, project: Project) -> None:
        client = get_elasticsearch_client()
        if client is None:
            return
        document = {
            "slug": project.slug,
            "title_ru": project.title_ru,
            "title_en": project.title_en,
            "summary_ru": project.summary_ru,
            "summary_en": project.summary_en,
            "stack": project.stack,
            "is_published": project.is_published,
        }
        try:
            await client.index(index="projects", id=project.slug, document=document, refresh=True)
        except Exception:
            return

    async def index_blog_post(self, post: BlogPost) -> None:
        client = get_elasticsearch_client()
        if client is None:
            return
        document = {
            "slug": post.slug,
            "title_ru": post.title_ru,
            "title_en": post.title_en,
            "excerpt_ru": post.excerpt_ru,
            "excerpt_en": post.excerpt_en,
            "tags": post.tags,
            "is_published": post.is_published,
        }
        try:
            await client.index(index="blog_posts", id=post.slug, document=document, refresh=True)
        except Exception:
            return

    async def delete_document(self, index: str, doc_id: str) -> None:
        client = get_elasticsearch_client()
        if client is None:
            return
        try:
            await client.delete(index=index, id=doc_id, refresh=True)
        except NotFoundError:
            return
        except Exception:
            return

    async def search(self, index: str, query: str) -> list[dict[str, Any]]:
        client = get_elasticsearch_client()
        if client is None:
            return []
        try:
            response = await client.search(
                index=index,
                query={
                    "multi_match": {
                        "query": query,
                        "fields": ["title_ru^3", "title_en^3", "summary_ru", "summary_en", "excerpt_ru", "excerpt_en"],
                    }
                },
            )
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception:
            return []


search_service = SearchService()
