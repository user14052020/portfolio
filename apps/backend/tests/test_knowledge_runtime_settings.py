from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.services.knowledge_runtime_settings import (
    DatabaseKnowledgeRuntimeSettingsProvider,
    KnowledgeRuntimeSettingsService,
)


class _FakeSession:
    pass


class _FakeSiteSettingsRepository:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            id=1,
            created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            knowledge_runtime_flags_json={},
            knowledge_provider_priorities_json={"style_ingestion": 10},
        )
        self.updated_payload: dict[str, object] | None = None

    async def get_or_create_singleton(self, session):
        return self.settings

    async def update(self, session, instance, data):
        self.updated_payload = data
        for key, value in data.items():
            setattr(instance, key, value)
        return instance


class KnowledgeRuntimeSettingsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_reads_defaults_from_site_settings_payload(self) -> None:
        repository = _FakeSiteSettingsRepository()
        service = KnowledgeRuntimeSettingsService(repository=repository)

        settings = await service.read(_FakeSession())

        self.assertTrue(settings.style_ingestion_enabled)
        self.assertFalse(settings.malevich_enabled)
        self.assertFalse(settings.fashion_historian_enabled)
        self.assertFalse(settings.stylist_enabled)
        self.assertFalse(settings.use_editorial_knowledge)
        self.assertTrue(settings.use_historical_context)
        self.assertTrue(settings.use_color_poetics)
        self.assertEqual(settings.normalized_provider_priorities()["style_ingestion"], 10)

    async def test_service_updates_flags_and_priority_overrides(self) -> None:
        repository = _FakeSiteSettingsRepository()
        service = KnowledgeRuntimeSettingsService(repository=repository)

        settings = await service.update(
            _FakeSession(),
            payload={
                "style_ingestion_enabled": True,
                "malevich_enabled": True,
                "fashion_historian_enabled": True,
                "stylist_enabled": False,
                "use_editorial_knowledge": True,
                "use_historical_context": False,
                "use_color_poetics": True,
                "provider_priorities": {
                    "style_ingestion": 12,
                    "malevich": 5,
                },
            },
        )

        assert repository.updated_payload is not None
        self.assertEqual(
            repository.updated_payload["knowledge_runtime_flags_json"],
            {
                "style_ingestion_enabled": True,
                "malevich_enabled": True,
                "fashion_historian_enabled": True,
                "stylist_enabled": False,
                "use_editorial_knowledge": True,
                "use_historical_context": False,
                "use_color_poetics": True,
            },
        )
        self.assertEqual(
            repository.updated_payload["knowledge_provider_priorities_json"]["malevich"],
            5,
        )
        self.assertTrue(settings.malevich_enabled)
        self.assertFalse(settings.use_historical_context)
        self.assertEqual(settings.normalized_provider_priorities()["style_ingestion"], 12)

    async def test_database_provider_exposes_flags_and_priorities_for_registry(self) -> None:
        repository = _FakeSiteSettingsRepository()
        repository.settings.knowledge_runtime_flags_json = {
            "style_ingestion_enabled": True,
            "malevich_enabled": False,
            "fashion_historian_enabled": True,
            "stylist_enabled": False,
            "use_editorial_knowledge": True,
            "use_historical_context": True,
            "use_color_poetics": False,
        }
        repository.settings.knowledge_provider_priorities_json = {
            "style_ingestion": 14,
            "fashion_historian": 6,
        }
        provider = DatabaseKnowledgeRuntimeSettingsProvider(
            session=_FakeSession(),
            service=KnowledgeRuntimeSettingsService(repository=repository),
        )

        runtime_flags = await provider.get_runtime_flags()
        priorities = await provider.get_provider_priorities()

        self.assertTrue(runtime_flags.fashion_historian_enabled)
        self.assertTrue(runtime_flags.use_editorial_knowledge)
        self.assertFalse(runtime_flags.use_color_poetics)
        self.assertEqual(priorities["fashion_historian"], 6)


if __name__ == "__main__":
    unittest.main()
