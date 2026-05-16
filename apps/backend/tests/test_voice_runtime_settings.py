from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from app.services.voice_runtime_settings import (
    DatabaseVoiceRuntimeSettingsProvider,
    VoiceRuntimeSettingsService,
)


class _FakeSession:
    pass


class _FakeSiteSettingsRepository:
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            id=1,
            created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
            voice_runtime_flags_json={},
        )
        self.updated_payload: dict[str, object] | None = None

    async def get_or_create_singleton(self, session):
        return self.settings

    async def update(self, session, instance, data):
        self.updated_payload = data
        for key, value in data.items():
            setattr(instance, key, value)
        return instance


class VoiceRuntimeSettingsServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_service_reads_defaults_from_site_settings_payload(self) -> None:
        repository = _FakeSiteSettingsRepository()
        service = VoiceRuntimeSettingsService(repository=repository)

        settings = await service.read(_FakeSession())

        self.assertTrue(settings.historian_enabled)
        self.assertTrue(settings.color_poetics_enabled)
        self.assertTrue(settings.deep_mode_enabled)
        self.assertFalse(settings.cta_experimental_copy_enabled)

    async def test_service_updates_voice_runtime_flags(self) -> None:
        repository = _FakeSiteSettingsRepository()
        service = VoiceRuntimeSettingsService(repository=repository)

        settings = await service.update(
            _FakeSession(),
            payload={
                "historian_enabled": False,
                "color_poetics_enabled": False,
                "deep_mode_enabled": False,
                "cta_experimental_copy_enabled": True,
            },
        )

        assert repository.updated_payload is not None
        self.assertEqual(
            repository.updated_payload["voice_runtime_flags_json"],
            {
                "historian_enabled": False,
                "color_poetics_enabled": False,
                "deep_mode_enabled": False,
                "cta_experimental_copy_enabled": True,
            },
        )
        self.assertFalse(settings.historian_enabled)
        self.assertFalse(settings.color_poetics_enabled)
        self.assertFalse(settings.deep_mode_enabled)
        self.assertTrue(settings.cta_experimental_copy_enabled)

    async def test_database_provider_exposes_runtime_flags(self) -> None:
        repository = _FakeSiteSettingsRepository()
        repository.settings.voice_runtime_flags_json = {
            "historian_enabled": False,
            "color_poetics_enabled": True,
            "deep_mode_enabled": False,
            "cta_experimental_copy_enabled": True,
        }
        provider = DatabaseVoiceRuntimeSettingsProvider(
            session=_FakeSession(),
            service=VoiceRuntimeSettingsService(repository=repository),
        )

        flags = await provider.get_runtime_flags()

        self.assertFalse(flags.historian_enabled)
        self.assertTrue(flags.color_poetics_enabled)
        self.assertFalse(flags.deep_mode_enabled)
        self.assertTrue(flags.cta_experimental_copy_enabled)


if __name__ == "__main__":
    unittest.main()
