from app.domain.prompt_building.entities.fashion_brief import FashionBrief
from app.domain.prompt_building.entities.visual_outfit_contract import (
    VisualOutfitContract,
    VisualOutfitItem,
    VisualOutfitCategory,
)


class VisualOutfitContractBuilder:
    """Builds the visual source-of-truth that prompt rendering must preserve."""

    def build(self, *, brief: FashionBrief) -> VisualOutfitContract:
        locked_items: list[VisualOutfitItem] = []
        seen: set[str] = set()

        self._extend_items(
            locked_items,
            seen,
            values=brief.hero_garments,
            category="garment",
            role="hero",
        )
        self._extend_items(
            locked_items,
            seen,
            values=brief.garment_list,
            category="garment",
            role="outfit",
        )
        self._extend_items(
            locked_items,
            seen,
            values=brief.secondary_garments,
            category="garment",
            role="secondary",
        )
        self._extend_items(
            locked_items,
            seen,
            values=brief.footwear,
            category="footwear",
            role="footwear",
        )
        self._extend_items(
            locked_items,
            seen,
            values=brief.accessories,
            category="accessory",
            role="accessory",
        )
        self._extend_items(
            locked_items,
            seen,
            values=brief.props,
            category="prop",
            role="prop",
            required=False,
        )

        required_count = sum(1 for item in locked_items if item.required)
        negative_constraints = []
        if required_count:
            negative_constraints.append(
                "do not omit, replace, recolor, duplicate, or invent alternatives to locked outfit items"
            )

        return VisualOutfitContract(
            locked_items=locked_items[:10],
            palette=self._unique(brief.palette)[:6],
            materials=self._unique(brief.materials)[:6],
            silhouette=brief.silhouette,
            negative_constraints=negative_constraints,
            source_brief_hash=brief.content_hash(),
        )

    def _extend_items(
        self,
        result: list[VisualOutfitItem],
        seen: set[str],
        *,
        values: list[str],
        category: VisualOutfitCategory,
        role: str,
        required: bool = True,
    ) -> None:
        for value in values:
            label = self._clean(value)
            key = self._key(label)
            if not label or key in seen:
                continue
            seen.add(key)
            result.append(
                VisualOutfitItem(
                    label=label,
                    category=category,
                    role=role,
                    required=required,
                )
            )

    def _unique(self, values: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = self._clean(value)
            key = self._key(cleaned)
            if not cleaned or key in seen:
                continue
            seen.add(key)
            result.append(cleaned)
        return result

    def _clean(self, value: object) -> str:
        return str(value or "").strip()

    def _key(self, value: str) -> str:
        return " ".join(value.lower().split())
