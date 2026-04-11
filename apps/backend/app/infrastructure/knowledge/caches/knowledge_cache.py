from app.domain.knowledge.entities import KnowledgeBundle


class InMemoryKnowledgeCache:
    def __init__(self) -> None:
        self._cache: dict[str, KnowledgeBundle] = {}

    async def get(self, *, cache_key: str) -> KnowledgeBundle | None:
        cached = self._cache.get(cache_key)
        if cached is None:
            return None
        return cached.model_copy(deep=True)

    async def set(self, *, cache_key: str, bundle: KnowledgeBundle) -> None:
        self._cache[cache_key] = bundle.model_copy(deep=True)
