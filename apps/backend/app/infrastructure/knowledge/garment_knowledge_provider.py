from app.application.stylist_chat.contracts.ports import GarmentKnowledgeProvider, KnowledgeItem, KnowledgeResult
from app.domain.garment_matching.entities.anchor_garment import AnchorGarment


class StaticGarmentKnowledgeProvider(GarmentKnowledgeProvider):
    async def fetch_for_anchor_garment(
        self,
        garment: AnchorGarment,
        context: dict | None = None,
    ) -> KnowledgeResult:
        items: list[KnowledgeItem] = [
            KnowledgeItem(
                "balance",
                "Balance the anchor garment with one supportive layer and one calm base so the outfit stays readable.",
            ),
            KnowledgeItem(
                "restraint",
                "Keep accessories quieter than the anchor garment and avoid repeating the same material everywhere.",
            ),
        ]
        if garment.material == "linen":
            items.append(
                KnowledgeItem("fabric", "Support linen with breathable, matte textures and lighter footwear weight.")
            )
        elif garment.material == "leather":
            items.append(
                KnowledgeItem("fabric", "Balance leather with softer supporting fabrics so the look does not feel heavy.")
            )
        if garment.formality == "formal":
            items.append(
                KnowledgeItem("formality", "Keep silhouette polish consistent from outer layer to footwear.")
            )
        elif garment.formality == "casual":
            items.append(
                KnowledgeItem("formality", "Keep the anchor casual and elevate the outfit through cleaner proportions.")
            )
        return KnowledgeResult(
            items=items,
            source="garment_static_knowledge",
            query={
                "garment": garment.model_dump(exclude_none=True),
                "context": context or {},
            },
        )
