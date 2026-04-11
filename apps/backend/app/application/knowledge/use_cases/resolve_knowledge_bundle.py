from app.domain.knowledge.entities import KnowledgeBundle, KnowledgeQuery


class ResolveKnowledgeBundleUseCase:
    def __init__(self, *, knowledge_retrieval_service) -> None:
        self.knowledge_retrieval_service = knowledge_retrieval_service

    async def execute(self, *, query: KnowledgeQuery) -> KnowledgeBundle:
        return await self.knowledge_retrieval_service.retrieve(query)
