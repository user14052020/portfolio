from typing import Any

from app.application.stylist_chat.contracts.ports import KnowledgeResult, OutfitBriefBuilder
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment
from app.domain.garment_matching.entities.garment_matching_outfit_brief import GarmentMatchingOutfitBrief


class GarmentBriefCompiler(OutfitBriefBuilder):
    async def build(
        self,
        garment: AnchorGarment,
        context: dict[str, Any],
        knowledge_result: KnowledgeResult,
    ) -> GarmentMatchingOutfitBrief:
        color_value = garment.color_primary or garment.material or "anchor"
        styling_goal = (
            f"Build a complete outfit around the {color_value} {garment.garment_type or 'garment'} "
            f"while keeping the look coherent, wearable, and visually balanced."
        )
        return GarmentMatchingOutfitBrief(
            anchor_garment=garment,
            styling_goal=styling_goal,
            harmony_rules=[item.text for item in knowledge_result.items[:2]],
            color_logic=self._color_logic(garment),
            silhouette_balance=self._silhouette_balance(garment),
            complementary_garments=self._complementary_garments(garment),
            footwear_options=self._footwear_options(garment),
            accessories=self._accessories(garment),
            negative_constraints=[
                "Avoid duplicate garment categories and visually clashing textures.",
                "Do not overpower the anchor garment with louder statement pieces.",
            ],
            historical_reference=[
                "Use one clear visual anchor and one supporting layer for editorial coherence."
            ],
            tailoring_notes=self._tailoring_notes(garment, context),
            image_prompt_notes=[
                "Luxury editorial flat lay, garments only, overhead composition.",
                "One complete outfit only, readable styling hierarchy, no clutter.",
            ],
        )

    def compile(self, outfit_brief: GarmentMatchingOutfitBrief) -> dict[str, Any]:
        anchor_summary_bits = [
            outfit_brief.anchor_garment.color_primary,
            outfit_brief.anchor_garment.material,
            outfit_brief.anchor_garment.garment_type,
            outfit_brief.anchor_garment.fit,
        ]
        anchor_summary = " ".join(str(bit).strip() for bit in anchor_summary_bits if bit).strip()
        return {
            "brief_type": "garment_matching",
            "anchor_summary": anchor_summary,
            "anchor_garment": outfit_brief.anchor_garment.model_dump(exclude_none=True),
            "styling_goal": outfit_brief.styling_goal,
            "harmony_rules": outfit_brief.harmony_rules,
            "color_logic": outfit_brief.color_logic,
            "silhouette_balance": outfit_brief.silhouette_balance,
            "complementary_garments": outfit_brief.complementary_garments,
            "footwear_options": outfit_brief.footwear_options,
            "accessories": outfit_brief.accessories,
            "negative_constraints": outfit_brief.negative_constraints,
            "historical_reference": outfit_brief.historical_reference,
            "tailoring_notes": outfit_brief.tailoring_notes,
            "image_prompt_notes": outfit_brief.image_prompt_notes,
        }

    def _complementary_garments(self, garment: AnchorGarment) -> list[str]:
        if garment.category == "outerwear":
            return ["clean knit or tee", "straight trousers", "textural base layer"]
        if garment.category == "tailoring":
            return ["refined knit or shirt", "clean trousers or skirt", "lightweight outer layer"]
        if garment.category == "tops":
            return ["structured outer layer", "clean trousers or denim", "supporting base layer"]
        return ["balanced supporting layer", "clean bottom", "one textural accent"]

    def _footwear_options(self, garment: AnchorGarment) -> list[str]:
        if garment.formality == "formal":
            return ["polished leather shoes", "sleek ankle boots"]
        if garment.material == "leather":
            return ["minimal boots", "clean leather sneakers"]
        return ["minimal sneakers", "loafer or low boot"]

    def _accessories(self, garment: AnchorGarment) -> list[str]:
        items = ["structured belt", "compact bag"]
        if garment.category == "tailoring":
            items.append("restrained watch")
        if garment.material == "linen":
            items.append("textured summer tote")
        return items

    def _color_logic(self, garment: AnchorGarment) -> list[str]:
        notes = ["Echo one anchor tone in footwear or accessories instead of matching everything exactly."]
        if garment.color_primary:
            notes.append(f"Keep {garment.color_primary} as the visual anchor and support it with calmer neutrals.")
        if garment.color_secondary:
            notes.append(f"Use {', '.join(garment.color_secondary[:2])} only as secondary accents.")
        return notes

    def _silhouette_balance(self, garment: AnchorGarment) -> list[str]:
        if garment.fit == "oversized":
            return ["Balance volume with a cleaner lower half and contained footwear."]
        if garment.fit == "slim":
            return ["Avoid overly tight supporting pieces; keep one relaxed counterweight."]
        return ["Keep one structured and one relaxed element so the outfit reads intentional."]

    def _tailoring_notes(self, garment: AnchorGarment, context: dict[str, Any]) -> list[str]:
        notes = ["Prioritize clean proportions and visible separation between anchor and supporting pieces."]
        gender = str((context.get("profile_context") or {}).get("gender") or "").strip().lower()
        if gender == "male":
            notes.append("Keep menswear proportions and avoid feminine-coded accessory styling.")
        elif gender == "female":
            notes.append("Keep womenswear proportions and avoid bulky menswear-only tailoring cues.")
        if garment.seasonality:
            notes.append(f"Respect the {', '.join(garment.seasonality[:2])} seasonal weight of the outfit.")
        return notes
