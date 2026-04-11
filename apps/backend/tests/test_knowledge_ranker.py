import unittest

from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.domain.knowledge.entities import KnowledgeCard, KnowledgeQuery
from app.domain.knowledge.enums import KnowledgeType


class KnowledgeRankerTests(unittest.TestCase):
    def test_style_id_match_and_anchor_match_rank_higher(self) -> None:
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

        ranked = KnowledgeRanker().rank(cards=[generic, preferred], query=query)

        self.assertEqual(ranked[0].style_id, "soft-retro-prep")

    def test_diversity_penalty_pushes_repeated_traits_down(self) -> None:
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

        ranked = KnowledgeRanker().rank(cards=[repeated, fresher], query=query)

        self.assertEqual(ranked[0].style_id, "fresh-style")
