class CompileImagePromptUseCase:
    def __init__(self, *, image_prompt_compiler) -> None:
        self.image_prompt_compiler = image_prompt_compiler

    async def execute(self, *, brief):
        return await self.image_prompt_compiler.compile(brief=brief)
