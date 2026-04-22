from pathlib import Path
import inspect
import unittest

from app.domain.interaction_throttle import InteractionThrottleService as InteractionThrottlePolicy
from app.domain.stylist_runtime_settings import StylistRuntimeLimits
from app.domain.usage_access_policy import UsageAccessPolicyService as UsageAccessPolicy
from app.ingestion.styles.style_chatgpt_payloads import StyleEnrichmentPayload
from app.models.style_fashion_item_facets import StyleFashionItemFacet
from app.models.style_image_facets import StyleImageFacet
from app.models.style_knowledge_facets import StyleKnowledgeFacet
from app.models.style_presentation_facets import StylePresentationFacet
from app.models.style_relation_facets import StyleRelationFacet
from app.models.style_visual_facets import StyleVisualFacet
from app.services.stylist_conversational import StylistService


class RuntimeArchitectureContractsTests(unittest.TestCase):
    def test_domain_layer_exposes_typed_payload_facets_and_runtime_policy_entities(self) -> None:
        payload_schema = StyleEnrichmentPayload.model_fields

        self.assertIn("knowledge", payload_schema)
        self.assertIn("visual_language", payload_schema)
        self.assertIn("fashion_items", payload_schema)
        self.assertIn("image_generation", payload_schema)
        self.assertIn("relations", payload_schema)
        self.assertIn("presentation", payload_schema)
        self.assertTrue(hasattr(StyleKnowledgeFacet, "__tablename__"))
        self.assertTrue(hasattr(StyleVisualFacet, "__tablename__"))
        self.assertTrue(hasattr(StyleFashionItemFacet, "__tablename__"))
        self.assertTrue(hasattr(StyleImageFacet, "__tablename__"))
        self.assertTrue(hasattr(StyleRelationFacet, "__tablename__"))
        self.assertTrue(hasattr(StylePresentationFacet, "__tablename__"))
        self.assertTrue(inspect.isclass(StylistRuntimeLimits))
        self.assertTrue(inspect.isclass(UsageAccessPolicy))
        self.assertTrue(inspect.isclass(InteractionThrottlePolicy))

    def test_stylist_service_depends_on_policy_services_via_constructor_injection(self) -> None:
        signature = inspect.signature(StylistService)

        self.assertIn("usage_access_policy_service", signature.parameters)
        self.assertIn("interaction_throttle_service", signature.parameters)
        self.assertIn("runtime_policy_observability", signature.parameters)
        for parameter_name in (
            "usage_access_policy_service",
            "interaction_throttle_service",
            "runtime_policy_observability",
        ):
            self.assertEqual(signature.parameters[parameter_name].kind, inspect.Parameter.KEYWORD_ONLY)

        usage_policy = object()
        throttle_policy = object()
        observability = object()
        service = StylistService(
            usage_access_policy_service=usage_policy,
            interaction_throttle_service=throttle_policy,
            runtime_policy_observability=observability,
        )

        self.assertIs(service.usage_access_policy_service, usage_policy)
        self.assertIs(service.interaction_throttle_service, throttle_policy)
        self.assertIs(service.runtime_policy_observability, observability)

    def test_runtime_application_layers_do_not_import_raw_db_tables_directly(self) -> None:
        backend_root = Path(__file__).resolve().parents[1]
        runtime_application_dirs = [
            backend_root / "app" / "application" / "prompt_building",
            backend_root / "app" / "application" / "visual_generation",
        ]
        forbidden_markers = ("from app.models", "import app.models", "from sqlalchemy", "import sqlalchemy")
        violations: list[str] = []

        for directory in runtime_application_dirs:
            for path in directory.rglob("*.py"):
                source = path.read_text(encoding="utf-8")
                if any(marker in source for marker in forbidden_markers):
                    violations.append(str(path.relative_to(backend_root)))

        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
