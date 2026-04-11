import unittest

from app.application.knowledge.services.knowledge_bundle_builder import KnowledgeBundleBuilder
from app.application.knowledge.services.knowledge_ranker import KnowledgeRanker
from app.application.knowledge.services.knowledge_retrieval_service import DefaultKnowledgeRetrievalService
from app.application.knowledge.use_cases.build_knowledge_query import BuildKnowledgeQueryUseCase
from app.application.knowledge.use_cases.inject_knowledge_into_reasoning import InjectKnowledgeIntoReasoningUseCase
from app.application.knowledge.use_cases.resolve_knowledge_bundle import ResolveKnowledgeBundleUseCase
from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.results.decision_result import DecisionType
from app.domain.chat_context import StyleDirectionContext
from app.domain.chat_modes import ChatMode, FlowState
from app.domain.knowledge.entities import KnowledgeCard
from app.domain.knowledge.enums import KnowledgeType

try:
    from test_stylist_orchestrator import build_test_orchestrator
except ModuleNotFoundError:
    from tests.test_stylist_orchestrator import build_test_orchestrator


class FakeStyleCatalogRepository:
    def __init__(self, cards: list[KnowledgeCard]) -> None:
        self.cards = list(cards)

    async def search(self, *, query):
        if query.style_id:
            return [card for card in self.cards if card.style_id == query.style_id][: query.limit]
        if query.anchor_garment:
            tokens = {str(value).strip().lower() for value in query.anchor_garment.values() if isinstance(value, str)}
            return [card for card in self.cards if self._matches(card, tokens)][: query.limit]
        if query.occasion_context:
            tokens = {str(value).strip().lower() for value in query.occasion_context.values() if isinstance(value, str)}
            return [card for card in self.cards if self._matches(card, tokens)][: query.limit]
        return self.cards[: query.limit]

    async def list_candidate_styles(self, *, limit, exclude_style_ids=None):
        excluded = {item.strip().lower() for item in (exclude_style_ids or []) if isinstance(item, str) and item.strip()}
        result: list[KnowledgeCard] = []
        for card in self.cards:
            style_id = (card.style_id or "").strip().lower()
            if style_id and style_id in excluded:
                continue
            result.append(card)
            if len(result) >= limit:
                break
        return result

    def _matches(self, card: KnowledgeCard, tokens: set[str]) -> bool:
        haystack = " ".join([card.title, card.summary, " ".join(card.tags)]).lower()
        return any(token and token in haystack for token in tokens)


class FakeDerivedKnowledgeRepository:
    def __init__(self, cards: list[KnowledgeCard]) -> None:
        self.cards = list(cards)

    async def search(self, *, query, context_style_cards=None):
        style_ids = {
            card.style_id
            for card in (context_style_cards or [])
            if isinstance(card.style_id, str) and card.style_id.strip()
        }
        if query.style_id:
            style_ids.add(query.style_id)
        if style_ids:
            matched = [card for card in self.cards if card.style_id in style_ids]
            if matched:
                return matched[: query.limit]
        return self.cards[: query.limit]


class KnowledgeBackedStyleHistoryProvider:
    def __init__(self, cards: list[KnowledgeCard]) -> None:
        self.cards = list(cards)
        self.persisted_history: list[StyleDirectionContext] = []

    async def get_recent(self, session_id: str):
        return [item.model_copy(deep=True) for item in self.persisted_history[-5:]]

    async def pick_next(self, *, session_id: str, style_history: list[StyleDirectionContext]):
        excluded = {
            item.style_id.strip().lower()
            for item in style_history[-5:]
            if isinstance(item.style_id, str) and item.style_id.strip()
        }
        for card in self.cards:
            style_id = (card.style_id or "").strip().lower()
            if style_id and style_id not in excluded:
                return self._to_style_direction(card), card
        return self._to_style_direction(self.cards[0]), self.cards[0]

    async def record_exposure(self, *, session_id: str, style_direction) -> None:
        if isinstance(style_direction, KnowledgeCard):
            self.persisted_history.append(self._to_style_direction(style_direction))

    def _to_style_direction(self, card: KnowledgeCard) -> StyleDirectionContext:
        metadata = card.metadata or {}
        return StyleDirectionContext(
            style_id=card.style_id,
            style_name=card.title,
            style_family=str(metadata.get("canonical_name") or "").strip() or None,
            palette=[str(item) for item in metadata.get("palette", [])][:4],
            silhouette_family=str(metadata.get("silhouette_family") or "").strip() or None,
            hero_garments=[str(item) for item in metadata.get("hero_garments", [])][:4],
            footwear=[str(item) for item in metadata.get("footwear", [])][:3],
            accessories=[str(item) for item in metadata.get("accessories", [])][:3],
            materials=[str(item) for item in metadata.get("materials", [])][:4],
            styling_mood=[str(item) for item in metadata.get("mood_keywords", [])][:3],
            composition_type="editorial flat lay",
            background_family="editorial surface",
            layout_density="balanced",
            camera_distance="medium overhead",
            visual_preset=str(metadata.get("visual_preset") or "editorial_studio"),
        )


def make_style_card(style_id: str, title: str, palette: list[str], garments: list[str], materials: list[str], silhouette: str, preset: str, tags: list[str]) -> KnowledgeCard:
    return KnowledgeCard(
        id=f"style_catalog:{style_id}",
        knowledge_type=KnowledgeType.STYLE_CATALOG,
        title=title,
        summary=f"{title} style profile.",
        style_id=style_id,
        tags=list(tags),
        source_ref=f"https://knowledge.test/{style_id}",
        metadata={
            "canonical_name": title.lower(),
            "palette": list(palette),
            "hero_garments": list(garments),
            "materials": list(materials),
            "footwear": ["loafers"] if "prep" in style_id else ["derbies"],
            "accessories": ["belt"],
            "silhouette_family": silhouette,
            "mood_keywords": ["editorial", "curated"],
            "visual_preset": preset,
            "negative_constraints": ["avoid neon"],
        },
    )


def make_related_card(knowledge_type: KnowledgeType, suffix: str, style_id: str, summary: str) -> KnowledgeCard:
    return KnowledgeCard(
        id=f"{knowledge_type.value}:{suffix}",
        knowledge_type=knowledge_type,
        title=suffix.replace("-", " ").title(),
        summary=summary,
        style_id=style_id,
        source_ref=f"https://knowledge.test/{suffix}",
    )


def configure_stage8_knowledge_runtime(orchestrator):
    style_cards = [
        make_style_card(
            "artful-minimalism",
            "Artful Minimalism",
            ["chalk", "charcoal"],
            ["structured coat"],
            ["wool"],
            "clean and elongated",
            "editorial_studio",
            ["minimal", "structured", "gallery"],
        ),
        make_style_card(
            "soft-retro-prep",
            "Soft Retro Prep",
            ["camel", "cream"],
            ["oxford shirt"],
            ["cotton"],
            "relaxed collegiate layering",
            "airy_catalog",
            ["prep", "camel", "oxford"],
        ),
        make_style_card(
            "leather-minimal",
            "Leather Minimal",
            ["black", "graphite"],
            ["leather jacket"],
            ["leather"],
            "clean jacket-led silhouette",
            "editorial_studio",
            ["jacket", "leather", "black"],
        ),
        make_style_card(
            "gallery-smart-casual",
            "Gallery Smart Casual",
            ["olive", "ink"],
            ["relaxed blazer"],
            ["cotton twill"],
            "polished relaxed tailoring",
            "dark_gallery",
            ["exhibition", "smart casual", "olive"],
        ),
    ]
    retrieval_service = DefaultKnowledgeRetrievalService(
        style_catalog_repository=FakeStyleCatalogRepository(style_cards),
        color_theory_repository=FakeDerivedKnowledgeRepository(
            [
                make_related_card(KnowledgeType.COLOR_THEORY, "soft-retro-prep-color", "soft-retro-prep", "Keep camel and cream calm and warm."),
                make_related_card(KnowledgeType.COLOR_THEORY, "gallery-smart-casual-color", "gallery-smart-casual", "Use olive with refined dark neutrals."),
            ]
        ),
        fashion_history_repository=FakeDerivedKnowledgeRepository(
            [
                make_related_card(KnowledgeType.FASHION_HISTORY, "artful-minimalism-history", "artful-minimalism", "Minimalist gallery dressing draws from precise modern tailoring."),
                make_related_card(KnowledgeType.FASHION_HISTORY, "soft-retro-prep-history", "soft-retro-prep", "Soft retro prep references collegiate heritage."),
            ]
        ),
        tailoring_principles_repository=FakeDerivedKnowledgeRepository(
            [
                make_related_card(KnowledgeType.TAILORING_PRINCIPLES, "leather-minimal-tailoring", "leather-minimal", "Balance the leather jacket with one clean base layer."),
                make_related_card(KnowledgeType.TAILORING_PRINCIPLES, "gallery-smart-casual-tailoring", "gallery-smart-casual", "Keep the silhouette polished but not rigid."),
            ]
        ),
        materials_fabrics_repository=FakeDerivedKnowledgeRepository(
            [
                KnowledgeCard(
                    id="materials:leather-minimal",
                    knowledge_type=KnowledgeType.MATERIALS_FABRICS,
                    title="Leather Support",
                    summary="Support leather with softer cotton texture.",
                    style_id="leather-minimal",
                    source_ref="https://knowledge.test/leather-materials",
                    metadata={"materials": ["leather", "cotton"]},
                )
            ]
        ),
        flatlay_patterns_repository=FakeDerivedKnowledgeRepository(
            [
                make_related_card(KnowledgeType.FLATLAY_PROMPT_PATTERNS, "artful-minimalism-flatlay", "artful-minimalism", "Use tight negative space and clean spacing."),
                make_related_card(KnowledgeType.FLATLAY_PROMPT_PATTERNS, "soft-retro-prep-flatlay", "soft-retro-prep", "Let garments breathe with softer spacing."),
            ]
        ),
        knowledge_ranker=KnowledgeRanker(),
        knowledge_bundle_builder=KnowledgeBundleBuilder(),
    )
    knowledge_query_builder = BuildKnowledgeQueryUseCase()
    resolve_knowledge_bundle = ResolveKnowledgeBundleUseCase(knowledge_retrieval_service=retrieval_service)
    inject_knowledge_into_reasoning = InjectKnowledgeIntoReasoningUseCase()
    history_provider = KnowledgeBackedStyleHistoryProvider(style_cards[:2])

    for handler in orchestrator.mode_router.handlers.values():
        handler.knowledge_query_builder = knowledge_query_builder
        handler.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle
        handler.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning

    style_handler = orchestrator.mode_router.handlers[ChatMode.STYLE_EXPLORATION]
    style_handler.style_history_provider = history_provider
    style_handler.select_candidate_style_use_case.style_history_provider = history_provider
    style_handler.select_candidate_style_use_case.candidate_selector.style_history_provider = history_provider

    garment_handler = orchestrator.mode_router.handlers[ChatMode.GARMENT_MATCHING]
    garment_handler.build_outfit_brief_use_case.knowledge_query_builder = knowledge_query_builder
    garment_handler.build_outfit_brief_use_case.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle
    garment_handler.build_outfit_brief_use_case.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning

    occasion_handler = orchestrator.mode_router.handlers[ChatMode.OCCASION_OUTFIT]
    occasion_handler.build_outfit_brief_use_case.knowledge_query_builder = knowledge_query_builder
    occasion_handler.build_outfit_brief_use_case.resolve_knowledge_bundle_use_case = resolve_knowledge_bundle
    occasion_handler.build_outfit_brief_use_case.inject_knowledge_into_reasoning_use_case = inject_knowledge_into_reasoning

    return history_provider


class KnowledgeLayerE2ETests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        (
            self.orchestrator,
            self.context_store,
            self.reasoner,
            self.scheduler,
            self.event_logger,
            self.metrics_recorder,
            self.checkpoint_writer,
        ) = build_test_orchestrator()
        self.history_provider = configure_stage8_knowledge_runtime(self.orchestrator)
        self.reasoner.route = "text_and_generation"

    async def run_command(self, command: ChatCommand):
        return await self.orchestrator.handle(command=command)

    async def test_style_exploration_uses_style_catalog_instead_of_generic_reasoning(self) -> None:
        response = await self.run_command(
            ChatCommand(
                session_id="stage8-style-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                client_message_id="stage8-style-1-start",
                command_id="stage8-style-1-start",
            )
        )

        bundle = self.reasoner.last_reasoning_input["knowledge_bundle"]
        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(response.job_id, "job-1")
        self.assertEqual(response.telemetry["knowledge_provider_used"], "knowledge_layer")
        self.assertEqual(bundle["style_cards"][0]["knowledge_type"], KnowledgeType.STYLE_CATALOG.value)
        self.assertEqual(bundle["history_cards"][0]["style_id"], "artful-minimalism")
        self.assertEqual(bundle["flatlay_cards"][0]["style_id"], "artful-minimalism")
        self.assertEqual(self.context_store.context.current_style_id, "artful-minimalism")
        self.assertTrue(self.context_store.context.last_retrieved_knowledge_refs)

    async def test_garment_matching_uses_anchor_garment_plus_retrieved_knowledge(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage8-garment-1",
                locale="en",
                message="Help me style an item",
                requested_intent=ChatMode.GARMENT_MATCHING,
                command_name="garment_matching",
                command_step="start",
                user_message_id=1,
                client_message_id="stage8-garment-1-start",
            )
        )
        response = await self.run_command(
            ChatCommand(
                session_id="stage8-garment-1",
                locale="en",
                message="A black leather jacket",
                user_message_id=2,
                client_message_id="stage8-garment-1-followup",
                command_id="stage8-garment-1-followup",
            )
        )

        bundle = self.reasoner.last_reasoning_input["knowledge_bundle"]
        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(bundle["style_cards"][0]["style_id"], "leather-minimal")
        self.assertEqual(bundle["tailoring_cards"][0]["knowledge_type"], KnowledgeType.TAILORING_PRINCIPLES.value)
        self.assertEqual(bundle["materials_cards"][0]["knowledge_type"], KnowledgeType.MATERIALS_FABRICS.value)
        self.assertEqual(response.telemetry["retrieved_tailoring_cards_count"], 1)
        self.assertEqual(response.telemetry["retrieved_material_cards_count"], 1)
        self.assertTrue(self.context_store.context.last_retrieved_knowledge_refs)

    async def test_occasion_outfit_uses_slot_context_and_retrieved_style_logic(self) -> None:
        await self.run_command(
            ChatCommand(
                session_id="stage8-occasion-1",
                locale="en",
                message="Help me dress for an occasion",
                requested_intent=ChatMode.OCCASION_OUTFIT,
                command_name="occasion_outfit",
                command_step="start",
                user_message_id=1,
                client_message_id="stage8-occasion-1-start",
            )
        )
        self.reasoner.occasion_output.event_type = "exhibition"
        self.reasoner.occasion_output.dress_code = "smart casual"
        self.reasoner.occasion_output.season_or_weather = "autumn"
        self.reasoner.occasion_output.time_of_day = "evening"
        self.reasoner.occasion_output.desired_impression = "polished"
        response = await self.run_command(
            ChatCommand(
                session_id="stage8-occasion-1",
                locale="en",
                message="It is an evening exhibition in autumn, smart casual and polished",
                user_message_id=2,
                client_message_id="stage8-occasion-1-followup",
                command_id="stage8-occasion-1-followup",
            )
        )

        bundle = self.reasoner.last_reasoning_input["knowledge_bundle"]
        self.assertEqual(response.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(bundle["style_cards"][0]["style_id"], "gallery-smart-casual")
        self.assertEqual(bundle["color_cards"][0]["knowledge_type"], KnowledgeType.COLOR_THEORY.value)
        self.assertEqual(bundle["tailoring_cards"][0]["knowledge_type"], KnowledgeType.TAILORING_PRINCIPLES.value)
        self.assertEqual(response.telemetry["retrieved_color_cards_count"], 1)
        self.assertEqual(response.telemetry["retrieved_tailoring_cards_count"], 1)

    async def test_retrieval_survives_provider_fallback(self) -> None:
        self.reasoner.raise_error = True
        response = await self.run_command(
            ChatCommand(
                session_id="stage8-fallback-1",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                client_message_id="stage8-fallback-1-start",
                command_id="stage8-fallback-1-start",
            )
        )

        self.assertTrue(response.telemetry["fallback_used"])
        self.assertTrue(response.telemetry["knowledge_query_hash"])
        self.assertTrue(response.telemetry["knowledge_bundle_hash"])
        self.assertEqual(
            self.event_logger.events[-1][1]["knowledge_bundle_hash"],
            response.telemetry["knowledge_bundle_hash"],
        )
        self.assertEqual(response.job_id, "job-1")

    async def test_anti_repeat_uses_traits_from_knowledge_layer_on_second_style_run(self) -> None:
        first = await self.run_command(
            ChatCommand(
                session_id="stage8-style-repeat",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=1,
                client_message_id="stage8-style-repeat-1",
                command_id="stage8-style-repeat-1",
            )
        )
        second = await self.run_command(
            ChatCommand(
                session_id="stage8-style-repeat",
                locale="en",
                message="Try another style",
                requested_intent=ChatMode.STYLE_EXPLORATION,
                command_name="style_exploration",
                command_step="start",
                user_message_id=2,
                client_message_id="stage8-style-repeat-2",
                command_id="stage8-style-repeat-2",
            )
        )

        self.assertEqual(first.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(second.decision_type, DecisionType.TEXT_AND_GENERATE)
        self.assertEqual(self.context_store.context.current_style_id, "soft-retro-prep")
        self.assertEqual(
            self.reasoner.last_reasoning_input["previous_style_directions"][-1]["palette"],
            ["chalk", "charcoal"],
        )
        constraints = self.scheduler.enqueued[-1].metadata["anti_repeat_constraints"]
        self.assertEqual(constraints["avoid_palette"], ["chalk", "charcoal"])
        self.assertEqual(constraints["avoid_hero_garments"], ["structured coat"])
        self.assertEqual(
            self.reasoner.last_reasoning_input["knowledge_bundle"]["style_cards"][0]["style_id"],
            "soft-retro-prep",
        )
        self.assertEqual(self.context_store.context.flow_state, FlowState.GENERATION_QUEUED)
