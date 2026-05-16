from typing import Literal

from pydantic import BaseModel, Field


VisualOutfitCategory = Literal["garment", "footwear", "accessory", "palette", "material", "prop", "other"]


class VisualOutfitItem(BaseModel):
    label: str
    category: VisualOutfitCategory = "other"
    role: str | None = None
    required: bool = True
    source: str = "fashion_brief"

    def render(self) -> str:
        prefix = f"{self.role} " if self.role else ""
        return f"{prefix}{self.category}: {self.label}"


class VisualOutfitContract(BaseModel):
    locked_items: list[VisualOutfitItem] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    materials: list[str] = Field(default_factory=list)
    silhouette: str | None = None
    negative_constraints: list[str] = Field(default_factory=list)
    source_brief_hash: str | None = None

    @property
    def has_required_items(self) -> bool:
        return any(item.required for item in self.locked_items)

    def required_item_labels(self) -> list[str]:
        return [item.label for item in self.locked_items if item.required]
