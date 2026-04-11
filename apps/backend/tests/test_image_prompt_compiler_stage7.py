import unittest

from app.application.prompt_building.services.image_prompt_compiler import ImagePromptCompiler
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class ImagePromptCompilerStage7Tests(unittest.IsolatedAsyncioTestCase):
    async def test_compile_creates_hashes_and_mode_specific_negative_prompt(self) -> None:
        compiler = ImagePromptCompiler()
        brief = FashionBrief(
            style_identity="Soft Retro Prep",
            style_family="soft prep",
            brief_mode="style_exploration",
            tailoring_logic=["relaxed collegiate layering"],
            color_logic=["keep camel and cream calm"],
            garment_list=["oxford shirt", "pleated chinos"],
            palette=["camel", "cream"],
            materials=["cotton"],
            footwear=["loafers"],
            accessories=["belt"],
            styling_notes=["soft, warm, collegiate"],
            composition_rules=["shift to textured surface"],
            negative_constraints=["avoid palette: chalk, charcoal"],
            diversity_constraints={"avoid_palette": ["chalk", "charcoal"], "force_visual_preset_shift": True},
            visual_preset="textured_surface",
            knowledge_cards=[{"key": "diversity", "text": "Shift palette."}],
            metadata={"diversity_constraints_hash": "abc123"},
        )

        compiled = await compiler.compile(brief=brief)

        self.assertIn("Soft Retro Prep", compiled.final_prompt)
        self.assertIn("avoid previous palette", compiled.negative_prompt)
        self.assertEqual(compiled.visual_preset, "textured_surface")
        self.assertTrue(compiled.metadata["brief_hash"])
        self.assertTrue(compiled.metadata["compiled_prompt_hash"])
