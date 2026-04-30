import unittest

from app.services.profile_context_payloads import merge_profile_context_sources
try:
    from app.services.stylist_conversational import StylistService
except ModuleNotFoundError:
    StylistService = None


class StylistServiceProfileContextTests(unittest.TestCase):
    def test_merge_profile_context_prefers_explicit_frontend_payload(self) -> None:
        merged = merge_profile_context_sources(
            explicit_profile_context={
                "presentation_profile": "androgynous",
                "fit_preferences": ["relaxed"],
            },
            derived_profile_context={
                "gender": "female",
                "height_cm": 172,
            },
        )

        self.assertEqual(
            merged,
            {
                "gender": "female",
                "height_cm": 172,
                "presentation_profile": "androgynous",
                "fit_preferences": ["relaxed"],
            },
        )

    def test_merge_profile_context_ignores_empty_explicit_values(self) -> None:
        merged = merge_profile_context_sources(
            explicit_profile_context={
                "presentation_profile": None,
                "fit_preferences": [],
            },
            derived_profile_context={
                "gender": "male",
                "height_cm": 180,
            },
        )

        self.assertEqual(
            merged,
            {
                "gender": "male",
                "height_cm": 180,
                "fit_preferences": [],
            },
        )


@unittest.skipIf(StylistService is None, "fastapi dependency is not available in this test environment")
class StylistServiceRuntimeProfileContextTests(unittest.TestCase):
    def test_runtime_profile_context_uses_resolved_session_profile_and_keeps_derived_body_hints(self) -> None:
        assert StylistService is not None
        service = StylistService()

        merged = service._build_runtime_profile_context(
            session_profile_context={
                "presentation_profile": "androgynous",
                "fit_preferences": ["relaxed"],
                "preferred_items": ["blazer"],
            },
            derived_profile_context={
                "gender": "female",
                "height_cm": 172,
            },
        )

        self.assertEqual(
            merged,
            {
                "gender": "female",
                "height_cm": 172,
                "presentation_profile": "androgynous",
                "fit_preferences": ["relaxed"],
                "preferred_items": ["blazer"],
            },
        )


if __name__ == "__main__":
    unittest.main()
