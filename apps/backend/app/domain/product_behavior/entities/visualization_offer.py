from pydantic import BaseModel


class VisualizationOffer(BaseModel):
    can_offer_visualization: bool = False
    cta_text: str | None = None
    visualization_type: str | None = None

