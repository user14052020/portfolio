import unittest

from app.application.prompt_building.services.prompt_validator import PromptValidator
from app.domain.prompt_building.entities.compiled_image_prompt import CompiledImagePrompt
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class PromptValidatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_validate_brief_catches_incomplete_generation_brief(self) -> None:
        validator = PromptValidator()
        brief = FashionBrief(
            style_identity="",
            brief_mode="garment_matching",
            garment_list=[],
            tailoring_logic=[],
            color_logic=[],
        )

        errors = await validator.validate_brief(brief)

        self.assertIn("style_identity is required", errors)
        self.assertIn("garment_list is required for generation-oriented modes", errors)
        self.assertIn("tailoring_logic is required for the selected mode", errors)

    async def test_validate_compiled_requires_hashes_and_visual_preset(self) -> None:
        validator = PromptValidator()
        compiled = CompiledImagePrompt(
            final_prompt="editorial outfit",
            negative_prompt="",
            visual_preset=None,
            metadata={},
        )

        errors = await validator.validate_compiled(compiled)

        self.assertIn("negative_prompt must not be empty", errors)
        self.assertIn("visual_preset is required", errors)
        self.assertIn("brief_hash is required for observability", errors)
