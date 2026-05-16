from app.application.knowledge.contracts import KnowledgeProvider, KnowledgeRuntimeSettingsProvider
from app.domain.knowledge.entities import KnowledgeRuntimeFlags


class DefaultKnowledgeProvidersRegistry:
    def __init__(
        self,
        *,
        providers: list[KnowledgeProvider],
        runtime_flags: KnowledgeRuntimeFlags | None = None,
        runtime_settings_provider: KnowledgeRuntimeSettingsProvider | None = None,
    ) -> None:
        self._providers = list(providers)
        self._runtime_flags = runtime_flags or KnowledgeRuntimeFlags()
        self._runtime_settings_provider = runtime_settings_provider

    async def get_enabled_runtime_providers(self) -> list[KnowledgeProvider]:
        runtime_flags = self._runtime_flags
        provider_priorities: dict[str, int] = {}
        if self._runtime_settings_provider is not None:
            runtime_flags = await self._runtime_settings_provider.get_runtime_flags()
            provider_priorities = await self._runtime_settings_provider.get_provider_priorities()
        ordered = sorted(
            self._providers,
            key=lambda provider: (
                0 if provider.config.code.strip().lower() == "style_ingestion" else 1,
                provider_priorities.get(
                    provider.config.code.strip().lower(),
                    provider.config.priority,
                ),
                provider.config.code,
            ),
        )
        enabled: list[KnowledgeProvider] = []
        seen_codes: set[str] = set()
        for provider in ordered:
            code = provider.config.code.strip().lower()
            if not provider.config.is_available_for_runtime():
                continue
            if not runtime_flags.allows_provider(provider.config):
                continue
            if code in seen_codes:
                continue
            seen_codes.add(code)
            enabled.append(provider)
        return enabled
