class ValidatePromptPipelineUseCase:
    def __init__(self, *, prompt_validator) -> None:
        self.prompt_validator = prompt_validator

    async def validate_brief(self, *, brief) -> list[str]:
        return await self.prompt_validator.validate_brief(brief)

    async def validate_compiled(self, *, compiled_prompt) -> list[str]:
        return await self.prompt_validator.validate_compiled(compiled_prompt)

    async def execute(self, *, brief, compiled_prompt=None) -> list[str]:
        errors = [*(await self.validate_brief(brief=brief))]
        if compiled_prompt is not None:
            errors.extend(await self.validate_compiled(compiled_prompt=compiled_prompt))
        return errors
