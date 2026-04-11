import unittest

from app.application.stylist_chat.services.candidate_style_selector import CandidateStyleSelector
from app.domain.chat_context import StyleDirectionContext


def make_style(style_id: str) -> StyleDirectionContext:
    return StyleDirectionContext(
        style_id=style_id,
        style_name=style_id.replace("-", " ").title(),
        palette=["navy", "cream"],
        hero_garments=["coat"],
        footwear=[],
        accessories=[],
        materials=[],
        styling_mood=[],
    )


class FakeStyleHistoryProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[StyleDirectionContext]]] = []

    async def pick_next(self, *, session_id: str, style_history: list[StyleDirectionContext]):
        self.calls.append((session_id, style_history))
        return make_style("soft-retro-prep"), {"source": "fake-db"}


class CandidateStyleSelectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_select_delegates_to_provider_with_recent_history(self) -> None:
        provider = FakeStyleHistoryProvider()
        selector = CandidateStyleSelector(provider)
        history = [make_style("artful-minimalism")]

        style_direction, source = await selector.select(
            session_id="style-selector-1",
            style_history=history,
        )

        self.assertEqual(style_direction.style_id, "soft-retro-prep")
        self.assertEqual(source, {"source": "fake-db"})
        self.assertEqual(provider.calls[0][0], "style-selector-1")
        self.assertEqual(provider.calls[0][1][0].style_id, "artful-minimalism")

