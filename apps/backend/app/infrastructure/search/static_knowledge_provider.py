from app.application.stylist_chat.contracts.ports import KnowledgeItem, KnowledgeProvider, KnowledgeResult


class StaticKnowledgeProvider(KnowledgeProvider):
    async def fetch(self, *, query: dict[str, object]) -> KnowledgeResult:
        mode = str(query.get("mode") or "general_advice")
        items: list[KnowledgeItem] = []
        if mode == "garment_matching":
            items = [
                KnowledgeItem("proportion", "Balance the anchor garment with one structured supporting layer and one clean base."),
                KnowledgeItem("color", "Echo one anchor tone in footwear or accessories instead of matching every item directly."),
            ]
        elif mode == "occasion_outfit":
            items = [
                KnowledgeItem("dress_code", "Respect the event formality first, then adjust personality through texture and accessories."),
                KnowledgeItem("clarity", "Occasion outfits read strongest when silhouette, footwear, and outer layer support the same level of polish."),
            ]
        elif mode == "style_exploration":
            items = [
                KnowledgeItem("diversity", "A fresh style direction should change palette, silhouette, and hero garment emphasis together."),
                KnowledgeItem("cohesion", "Keep one visual anchor so the outfit feels intentional instead of random."),
            ]
        else:
            items = [
                KnowledgeItem("general", "The fastest way to modernize an outfit is to simplify the silhouette and refine the footwear choice."),
            ]
        return KnowledgeResult(items=items, source="static_rules", query=query)
