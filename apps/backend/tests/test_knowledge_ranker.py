import unittest

from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


class KnowledgeRankerTests(unittest.IsolatedAsyncioTestCase):
    async def test_style_id_match_and_anchor_match_rank_higher(self) -> None:
        preferred = KnowledgeCard(
            id="style:soft-retro-prep",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Soft Retro Prep",
            summary="Warm collegiate prep.",
            tags=["soft retro prep", "camel", "loafer", "jacket"],
            style_id="soft-retro-prep",
            metadata={"palette": ["camel", "cream"], "hero_garments": ["jacket"]},
        )
        generic = KnowledgeCard(
            id="style:generic",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Generic Minimalism",
            summary="Neutral minimal style.",
            tags=["minimal", "grey"],
            style_id="generic-minimalism",
            metadata={"palette": ["grey"], "hero_garments": ["coat"]},
        )
        query = KnowledgeQuery(
            mode="garment_matching",
            style_id="soft-retro-prep",
            anchor_garment={"garment_type": "jacket", "color_primary": "camel"},
        )

        ranked = await KnowledgeRanker().rank(cards=[generic, preferred], query=query)

        self.assertEqual(ranked[0].style_id, "soft-retro-prep")

    async def test_diversity_penalty_pushes_repeated_traits_down(self) -> None:
        repeated = KnowledgeCard(
            id="style:repeated",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Repeated Palette",
            summary="Repeats the same look.",
            style_id="repeated-style",
            metadata={
                "palette": ["camel", "cream"],
                "hero_garments": ["oxford shirt"],
                "silhouette_family": "relaxed collegiate layering",
            },
        )
        fresher = KnowledgeCard(
            id="style:fresh",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Fresh Workwear",
            summary="A different direction.",
            style_id="fresh-style",
            metadata={
                "palette": ["olive", "ecru"],
                "hero_garments": ["overshirt"],
                "silhouette_family": "grounded utility layers",
            },
        )
        query = KnowledgeQuery(
            mode="style_exploration",
            diversity_constraints={
                "avoid_palette": ["camel", "cream"],
                "avoid_hero_garments": ["oxford shirt"],
                "avoid_silhouette_families": ["relaxed collegiate layering"],
            },
        )

        ranked = await KnowledgeRanker().rank(cards=[repeated, fresher], query=query)

        self.assertEqual(ranked[0].style_id, "fresh-style")

    async def test_profile_context_softly_reweights_cards_before_retrieval_bundle_is_built(self) -> None:
        avoided = KnowledgeCard(
            id="visual:heels",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Heeled Editorial Direction",
            summary="A feminine heel-forward silhouette with romantic polish.",
            style_id="heels-heavy",
            confidence=0.92,
            metadata={
                "silhouette_family": "soft romantic line",
                "hero_garments": ["heels", "slip skirt"],
                "palette": ["rose"],
            },
        )
        preferred = KnowledgeCard(
            id="visual:structured",
            knowledge_type=KnowledgeType.STYLE_CATALOG,
            title="Structured Androgynous Tailoring",
            summary="An androgynous structured silhouette with elongated tailoring and loafers.",
            style_id="structured-androgynous",
            confidence=0.8,
            metadata={
                "silhouette_family": "structured elongated line",
                "hero_garments": ["loafers", "tailored coat"],
                "palette": ["charcoal"],
            },
        )
        query = KnowledgeQuery(
            mode="style_exploration",
            profile_context={
                "presentation_profile": "androgynous",
                "silhouette_preferences": ["structured", "elongated"],
                "avoided_items": ["heels"],
            },
        )

        ranked = await KnowledgeRanker().rank(cards=[avoided, preferred], query=query)

        self.assertEqual(ranked[0].style_id, "structured-androgynous")

    async def test_provider_priority_breaks_relevance_ties_toward_higher_priority_provider(self) -> None:
        lower_priority = KnowledgeCard(
            id="history:low-priority",
            knowledge_type=KnowledgeType.FASHION_HISTORY,
            provider_code="fashion_historian",
            provider_priority=80,
            title="Historian Note",
            summary="Same historical note.",
            style_id="artful-minimalism",
        )
        higher_priority = KnowledgeCard(
            id="history:high-priority",
            knowledge_type=KnowledgeType.FASHION_HISTORY,
            provider_code="fashion_historian",
            provider_priority=20,
            title="Historian Note",
            summary="Same historical note.",
            style_id="artful-minimalism",
        )

        ranked = await KnowledgeRanker().rank(
            cards=[lower_priority, higher_priority],
            query=KnowledgeQuery(mode="general_advice", need_historical_knowledge=True),
        )

        self.assertEqual(ranked[0].id, "history:high-priority")

    async def test_diversity_promotes_different_knowledge_type_before_duplicate_type(self) -> None:
        first_visual = KnowledgeCard(
            id="visual:one",
            knowledge_type=KnowledgeType.STYLE_VISUAL_LANGUAGE,
            provider_code="style_ingestion",
            provider_priority=10,
            title="Visual One",
            summary="Muted palette and soft treatment.",
            style_id="soft-retro-prep",
        )
        second_visual = KnowledgeCard(
            id="visual:two",
            knowledge_type=KnowledgeType.STYLE_VISUAL_LANGUAGE,
            provider_code="style_ingestion",
            provider_priority=10,
            title="Visual Two",
            summary="Another muted palette and soft treatment.",
            style_id="soft-retro-prep",
        )
        historical = KnowledgeCard(
            id="history:one",
            knowledge_type=KnowledgeType.FASHION_HISTORY,
            provider_code="fashion_historian",
            provider_priority=20,
            title="History One",
            summary="A contextual history note.",
            style_id="soft-retro-prep",
        )

        ranked = await KnowledgeRanker().rank(
            cards=[first_visual, second_visual, historical],
            query=KnowledgeQuery(
                mode="style_exploration",
                need_visual_knowledge=True,
                need_historical_knowledge=True,
            ),
        )

        self.assertEqual(ranked[0].id, "visual:one")
        self.assertEqual(ranked[1].id, "history:one")
