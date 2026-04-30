import unittest

from app.domain.chat_context import ChatMode, ChatModeContext
from app.services.profile_session_state import ProfileSessionStateService


class ProfileSessionStateServiceTests(unittest.TestCase):
    def test_resolve_merges_backend_session_profile_with_request_hints_and_recent_updates(self) -> None:
        service = ProfileSessionStateService()

        state = self._run(
            service.resolve(
                context=ChatModeContext(
                    session_profile_context={
                        "presentation_profile": "androgynous",
                        "fit_preferences": ["relaxed"],
                        "avoided_items": ["heels"],
                    }
                ),
                explicit_profile_context={
                    "preferred_items": ["blazer"],
                },
                metadata={
                    "profile_recent_updates": {
                        "color_preferences": ["navy"],
                    }
                },
            )
        )

        self.assertEqual(
            state.session_profile_context,
            {
                "presentation_profile": "androgynous",
                "fit_preferences": ["relaxed"],
                "color_preferences": ["navy"],
                "preferred_items": ["blazer"],
                "avoided_items": ["heels"],
            },
        )
        self.assertEqual(
            state.profile_recent_updates,
            {
                "color_preferences": ["navy"],
            },
        )
        self.assertEqual(state.profile_completeness_state, "partial")
        self.assertIsNotNone(state.profile_context_snapshot)
        assert state.profile_context_snapshot is not None
        self.assertEqual(state.profile_context_snapshot["source"], "profile_context_service")
        self.assertEqual(state.profile_context_snapshot["fit_preferences"], ["relaxed"])

    def test_resolve_preserves_passthrough_profile_fields_in_session_state_and_snapshot(self) -> None:
        service = ProfileSessionStateService()

        state = self._run(
            service.resolve(
                context=ChatModeContext(
                    session_profile_context={
                        "presentation_profile": "androgynous",
                        "height_cm": 176,
                    }
                ),
                explicit_profile_context={
                    "preferred_items": ["blazer"],
                },
                metadata={
                    "profile_recent_updates": {
                        "weight_kg": 63,
                    }
                },
            )
        )

        self.assertEqual(
            state.session_profile_context,
            {
                "presentation_profile": "androgynous",
                "preferred_items": ["blazer"],
                "height_cm": 176,
                "weight_kg": 63,
            },
        )
        self.assertEqual(
            state.profile_recent_updates,
            {
                "weight_kg": 63,
            },
        )
        self.assertEqual(state.profile_completeness_state, "partial")
        assert state.profile_context_snapshot is not None
        self.assertEqual(state.profile_context_snapshot["values"]["height_cm"], 176)
        self.assertEqual(state.profile_context_snapshot["values"]["weight_kg"], 63)

    def test_chat_mode_reset_preserves_profile_session_state(self) -> None:
        context = ChatModeContext(
            active_mode=ChatMode.STYLE_EXPLORATION,
            session_profile_context={"presentation_profile": "unisex"},
            profile_context_snapshot={
                "present": True,
                "source": "profile_context_service",
                "values": {"presentation_profile": "unisex"},
            },
            profile_recent_updates={"fit_preferences": ["balanced"]},
            profile_completeness_state="partial",
        )

        reset = context.reset_for_mode(
            mode=ChatMode.GENERAL_ADVICE,
            requested_intent=None,
            should_auto_generate=False,
            command_context=None,
        )

        self.assertEqual(reset.session_profile_context, {"presentation_profile": "unisex"})
        self.assertEqual(reset.profile_recent_updates, {"fit_preferences": ["balanced"]})
        self.assertEqual(reset.profile_completeness_state, "partial")
        self.assertEqual(
            reset.profile_context_snapshot,
            {
                "present": True,
                "source": "profile_context_service",
                "values": {"presentation_profile": "unisex"},
            },
        )

    def _run(self, awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
