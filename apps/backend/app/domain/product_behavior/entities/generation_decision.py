from pydantic import BaseModel

from app.domain.product_behavior.entities.visualization_offer import VisualizationOffer


class GenerationDecision(BaseModel):
    should_generate: bool
    reason: str
    should_offer_cta: bool = False
    cta_text: str | None = None
    visualization_type: str | None = None

    def to_offer(self) -> VisualizationOffer | None:
        if not self.should_offer_cta:
            return None
        return VisualizationOffer(
            can_offer_visualization=True,
            cta_text=self.cta_text,
            visualization_type=self.visualization_type,
        )

