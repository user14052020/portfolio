from app.application.prompt_building.services.fashion_reasoning_service import FashionReasoningInput


class BuildFashionBriefUseCase:
    def __init__(self, *, fashion_reasoning_service) -> None:
        self.fashion_reasoning_service = fashion_reasoning_service

    async def execute(self, *, reasoning_input: FashionReasoningInput):
        return await self.fashion_reasoning_service.build_brief(reasoning_input=reasoning_input)
