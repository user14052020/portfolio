import unittest

from app.application.reasoning import (
    DefaultProfileClarificationPolicy,
    DefaultProfileContextNormalizer,
    DefaultProfileContextService,
    ProfileContextInput,
    ProfileContextUpdate,
)
from app.domain.reasoning import (
    PresentationProfile,
    ProfileContext,
    ProfileContextSnapshot,
    StyleAdviceFacet,
    StyleFacetBundle,
)


class ProfileContextLayerTests(unittest.TestCase):
    def test_normalizer_normalizes_legacy_payload_and_deduplicates_terms(self) -> None:
        normalizer = DefaultProfileContextNormalizer()

        profile = normalizer.normalize(
            {
                "gender": "female",
                "fit": "Relaxed",
                "silhouette": ["Structured", "structured", "unknown"],
                "comfort": "comfortable",
                "dress_code": "smart casual",
                "preferred_colors": "Navy, Cream, Navy",
                "avoid_colors": ["Neon", ""],
                "preferred_items": ["Blazer", "blazer", "wide-leg trousers"],
                "avoid_items": "Heels; micro bag",
                "unknown_field": "ignored",
            }
        )

        self.assertEqual(profile.presentation_profile, PresentationProfile.FEMININE)
        self.assertEqual(profile.fit_preferences, ["relaxed"])
        self.assertEqual(profile.silhouette_preferences, ["structured"])
        self.assertEqual(profile.comfort_preferences, ["high_comfort"])
        self.assertEqual(profile.formality_preferences, ["smart_casual"])
        self.assertEqual(profile.color_preferences, ["navy", "cream"])
        self.assertEqual(profile.color_avoidances, ["neon"])
        self.assertEqual(profile.preferred_items, ["blazer", "wide-leg trousers"])
        self.assertEqual(profile.avoided_items, ["heels", "micro bag"])

    def test_normalizer_drops_unknown_closed_set_values_and_limits_lists(self) -> None:
        normalizer = DefaultProfileContextNormalizer()

        update = ProfileContextUpdate(
            fit_preferences=["relaxed", "balanced", "unknown", "oversized", "fitted", "tailored"],
            color_preferences=[
                "navy",
                "cream",
                "charcoal",
                "olive",
                "burgundy",
                "silver",
                "sky blue",
                "black",
                "white",
            ],
        )
        profile = normalizer.normalize(update)

        self.assertEqual(
            profile.fit_preferences,
            ["relaxed", "balanced", "oversized", "fitted"],
        )
        self.assertEqual(
            profile.color_preferences,
            ["navy", "cream", "charcoal", "olive", "burgundy", "silver", "sky blue", "black"],
        )

    def test_normalizer_builds_snapshot_with_legacy_compatible_values(self) -> None:
        normalizer = DefaultProfileContextNormalizer()

        snapshot = normalizer.snapshot(
            {
                "presentation_profile": "androgynous",
                "fit": "balanced",
                "silhouette": "minimal",
                "comfort": "style first",
                "dress_code": "refined",
                "preferred_items": "long coat, silver loafers",
            },
            source="frontend_hints",
        )

        self.assertIsInstance(snapshot, ProfileContextSnapshot)
        self.assertTrue(snapshot.present)
        self.assertEqual(snapshot.source, "frontend_hints")
        self.assertEqual(snapshot.presentation_profile, "androgynous")
        self.assertEqual(snapshot.fit_preferences, ("balanced",))
        self.assertEqual(snapshot.values["fit"], "balanced")
        self.assertEqual(snapshot.values["dress_code"], "refined")
        self.assertEqual(
            snapshot.as_profile_context().presentation_profile,
            PresentationProfile.ANDROGYNOUS,
        )

    def test_normalizer_accepts_universal_presentation_alias(self) -> None:
        normalizer = DefaultProfileContextNormalizer()

        profile = normalizer.normalize(
            {
                "presentation_profile": "universal",
            }
        )

        self.assertEqual(profile.presentation_profile, PresentationProfile.UNISEX)

    def test_snapshot_coerces_universal_presentation_alias_to_unisex(self) -> None:
        snapshot = ProfileContextSnapshot(
            values={"presentation_profile": "universal"},
            present=True,
        )

        self.assertEqual(snapshot.presentation_profile, "unisex")
        self.assertEqual(snapshot.values["presentation_profile"], "unisex")
        self.assertEqual(
            snapshot.as_profile_context().presentation_profile,
            PresentationProfile.UNISEX,
        )

    def test_application_models_hold_profile_context_merge_inputs(self) -> None:
        session_profile = ProfileContext(
            presentation_profile=PresentationProfile.UNISEX,
            preferred_items=["clean sneakers"],
        )
        input_contract = ProfileContextInput(
            frontend_hints={"fit": "relaxed"},
            session_profile=session_profile,
            recent_updates={"avoid_items": "heels"},
        )

        self.assertEqual(input_contract.frontend_hints, {"fit": "relaxed"})
        self.assertEqual(input_contract.session_profile, session_profile)
        self.assertEqual(input_contract.recent_updates, {"avoid_items": "heels"})

    def test_profile_context_service_merges_sources_in_runtime_priority_order(self) -> None:
        service = DefaultProfileContextService()

        profile = self._run(
            service.build_context(
                ProfileContextInput(
                    persistent_profile=ProfileContext(
                        presentation_profile=PresentationProfile.MASCULINE,
                        fit_preferences=["fitted"],
                        preferred_items=["derby shoes"],
                    ),
                    session_profile=ProfileContext(
                        fit_preferences=["balanced"],
                        silhouette_preferences=["soft"],
                        preferred_items=["wide-leg trousers"],
                    ),
                    frontend_hints={
                        "fit": "relaxed",
                        "preferred_items": ["blazer"],
                    },
                    recent_updates={
                        "silhouette_preferences": ["structured"],
                        "avoid_items": "heels",
                    },
                )
            )
        )

        self.assertEqual(profile.presentation_profile, PresentationProfile.MASCULINE)
        self.assertEqual(profile.fit_preferences, ["relaxed"])
        self.assertEqual(profile.silhouette_preferences, ["structured"])
        self.assertEqual(profile.preferred_items, ["blazer"])
        self.assertEqual(profile.avoided_items, ["heels"])

    def test_profile_context_service_snapshot_returns_pipeline_ready_contract(self) -> None:
        service = DefaultProfileContextService()
        profile = ProfileContext(
            presentation_profile=PresentationProfile.UNISEX,
            fit_preferences=["balanced"],
            preferred_items=["long coat"],
        )

        snapshot = self._run(service.snapshot(profile))

        self.assertTrue(snapshot.present)
        self.assertEqual(snapshot.source, "profile_context_service")
        self.assertEqual(snapshot.values["fit"], "balanced")
        self.assertEqual(snapshot.values["preferred_items"], ["long coat"])

    def test_profile_context_service_build_snapshot_preserves_future_profile_fields(self) -> None:
        service = DefaultProfileContextService()

        snapshot = self._run(
            service.build_snapshot(
                ProfileContextInput(
                    session_profile={
                        "presentation_profile": "androgynous",
                        "height_cm": 176,
                    },
                    frontend_hints={
                        "fit": "relaxed",
                    },
                    recent_updates={
                        "weight_kg": 63,
                    },
                )
            )
        )

        self.assertTrue(snapshot.present)
        self.assertEqual(snapshot.presentation_profile, "androgynous")
        self.assertEqual(snapshot.fit_preferences, ("relaxed",))
        self.assertEqual(snapshot.values["height_cm"], 176)
        self.assertEqual(snapshot.values["weight_kg"], 63)
        self.assertEqual(snapshot.legacy_values, {"height_cm": 176, "weight_kg": 63})

    def test_profile_context_service_completeness_state_is_derived_in_profile_layer(self) -> None:
        service = DefaultProfileContextService()

        self.assertEqual(service.completeness_state_sync(None), "missing")
        self.assertEqual(
            service.completeness_state_sync(
                {
                    "presentation_profile": "androgynous",
                }
            ),
            "partial",
        )
        self.assertEqual(
            service.completeness_state_sync(
                {
                    "presentation_profile": "androgynous",
                    "fit_preferences": ["relaxed"],
                    "comfort_preferences": ["balanced"],
                }
            ),
            "strong",
        )

    def test_profile_clarification_policy_requests_silhouette_for_occasion_outfit(self) -> None:
        policy = DefaultProfileClarificationPolicy()

        decision = self._run(
            policy.evaluate(
                mode="occasion_outfit",
                profile=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    source="test",
                ),
                style_bundle=StyleFacetBundle(),
            )
        )

        self.assertTrue(decision.should_ask)
        self.assertEqual(
            decision.question_text,
            "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
        )
        self.assertEqual(decision.missing_priority_fields, ["silhouette_preferences"])

    def test_profile_clarification_policy_skips_general_advice_when_profile_is_missing(self) -> None:
        policy = DefaultProfileClarificationPolicy()

        decision = self._run(
            policy.evaluate(
                mode="general_advice",
                profile=None,
                style_bundle=StyleFacetBundle(),
            )
        )

        self.assertFalse(decision.should_ask)
        self.assertIsNone(decision.question_text)
        self.assertEqual(decision.missing_priority_fields, [])

    def test_profile_clarification_policy_requests_presentation_for_partial_style_exploration_profile(self) -> None:
        policy = DefaultProfileClarificationPolicy()

        decision = self._run(
            policy.evaluate(
                mode="style_exploration",
                profile=ProfileContextSnapshot(
                    silhouette_preferences=("structured",),
                    source="test",
                ),
                style_bundle=StyleFacetBundle(),
            )
        )

        self.assertTrue(decision.should_ask)
        self.assertEqual(
            decision.question_text,
            "Which presentation direction should guide this look: feminine, masculine, androgynous, or universal?",
        )
        self.assertEqual(decision.missing_priority_fields, ["presentation_profile"])

    def test_profile_clarification_policy_requests_wearability_for_branching_style_exploration_bundle(self) -> None:
        policy = DefaultProfileClarificationPolicy()

        decision = self._run(
            policy.evaluate(
                mode="style_exploration",
                profile=ProfileContextSnapshot(
                    presentation_profile="androgynous",
                    silhouette_preferences=("structured",),
                    source="test",
                ),
                style_bundle=StyleFacetBundle(
                    advice_facets=[
                        StyleAdviceFacet(
                            style_id=12,
                            casual_adaptations=["swap the heels for loafers"],
                            statement_pieces=["dramatic long coat"],
                        )
                    ]
                ),
            )
        )

        self.assertTrue(decision.should_ask)
        self.assertEqual(
            decision.question_text,
            "Do you want this to stay highly wearable, balanced, or a bit more expressive?",
        )
        self.assertEqual(decision.missing_priority_fields, ["comfort_preferences"])

    def _run(self, awaitable):
        import asyncio

        return asyncio.run(awaitable)


if __name__ == "__main__":
    unittest.main()
