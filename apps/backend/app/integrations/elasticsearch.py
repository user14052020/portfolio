from elasticsearch import AsyncElasticsearch

from app.core.config import get_settings


_es_client: AsyncElasticsearch | None = None


def get_elasticsearch_client() -> AsyncElasticsearch | None:
    global _es_client
    settings = get_settings()
    if not settings.enable_search_indexing:
        return None
    if _es_client is None:
        _es_client = AsyncElasticsearch(hosts=[settings.elasticsearch_url], request_timeout=5)
    return _es_client


async def close_elasticsearch_client() -> None:
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None

