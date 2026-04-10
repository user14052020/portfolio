from app.application.stylist_chat.contracts.ports import KnowledgeItem, KnowledgeResult, OccasionKnowledgeProvider
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext


class StaticOccasionKnowledgeProvider(OccasionKnowledgeProvider):
    async def fetch_for_occasion(
        self,
        context: OccasionContext,
        profile_context: dict | None = None,
    ) -> KnowledgeResult:
        items: list[KnowledgeItem] = [
            KnowledgeItem(
                "dress_code",
                "Respect the event formality first, then express personality through texture, palette, and accessories.",
            ),
            KnowledgeItem(
                "silhouette",
                "Occasion outfits feel strongest when silhouette, footwear, and outer layer confirm the same level of polish.",
            ),
        ]
        if context.weather_context in {"cold", "rainy", "windy"}:
            items.append(
                KnowledgeItem(
                    "weather",
                    "Let weather protection support polish instead of looking like an afterthought.",
                )
            )
        if context.event_type == "wedding":
            items.append(
                KnowledgeItem(
                    "wedding",
                    "Keep the outfit celebratory and refined without visually competing with the main hosts.",
                )
            )
        if context.dress_code == "smart casual":
            items.append(
                KnowledgeItem(
                    "smart-casual",
                    "Smart casual reads best with one tailored signal and one relaxed counterpart.",
                )
            )
        if context.desired_impression == "bold":
            items.append(
                KnowledgeItem(
                    "impression",
                    "Deliver boldness through one strong focal point and keep the rest clean enough to frame it.",
                )
            )
        return KnowledgeResult(
            items=items,
            source="occasion_static_knowledge",
            query={
                "occasion_context": context.model_dump(exclude_none=True),
                "profile_context": profile_context or {},
            },
        )
