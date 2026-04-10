from pydantic import BaseModel, Field, model_validator


class AnchorGarment(BaseModel):
    raw_user_text: str = ""
    garment_type: str | None = None
    category: str | None = None
    color_primary: str | None = None
    color_secondary: list[str] = Field(default_factory=list)
    material: str | None = None
    fit: str | None = None
    silhouette: str | None = None
    pattern: str | None = None
    seasonality: list[str] = Field(default_factory=list)
    formality: str | None = None
    gender_context: str | None = None
    style_hints: list[str] = Field(default_factory=list)
    asset_id: str | None = None
    confidence: float = 0.0
    completeness_score: float = 0.0
    is_sufficient_for_generation: bool = False
    color: str | None = None
    secondary_colors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def sync_compatibility_fields(self) -> "AnchorGarment":
        if self.color_primary is None and self.color is not None:
            self.color_primary = self.color
        if self.color is None and self.color_primary is not None:
            self.color = self.color_primary
        if not self.color_secondary and self.secondary_colors:
            self.color_secondary = list(self.secondary_colors)
        if not self.secondary_colors and self.color_secondary:
            self.secondary_colors = list(self.color_secondary)
        self.raw_user_text = self.raw_user_text.strip()
        return self

    def missing_attributes(self) -> list[str]:
        missing: list[str] = []
        if not self.garment_type:
            missing.append("garment_type")
        if not (self.color_primary or self.material):
            missing.append("color_or_material")
        if not (self.formality or self.seasonality or self.style_hints or self.asset_id):
            missing.append("styling_context")
        return missing
