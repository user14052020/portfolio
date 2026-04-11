from typing import Any

from app.application.prompt_building.services.fashion_reasoning_service import FashionReasoningInput
from app.domain.knowledge.entities import KnowledgeBundle
from app.domain.prompt_building.entities.fashion_brief import FashionBrief


class FashionBriefBuilder:
    COLOR_TOKENS = {
        "black",
        "white",
        "cream",
        "ivory",
        "navy",
        "blue",
        "indigo",
        "camel",
        "charcoal",
        "grey",
        "gray",
        "olive",
        "green",
        "brown",
        "tan",
        "beige",
        "burgundy",
        "red",
        "pink",
        "purple",
        "yellow",
        "orange",
        "forest",
        "ink",
        "chalk",
        "bone",
    }
    MATERIAL_TOKENS = {
        "wool",
        "cotton",
        "linen",
        "twill",
        "leather",
        "suede",
        "silk",
        "denim",
        "cashmere",
        "jersey",
        "canvas",
    }
    GARMENT_TOKENS = {
        "coat",
        "jacket",
        "shirt",
        "tee",
        "t-shirt",
        "trousers",
        "pants",
        "jeans",
        "skirt",
        "dress",
        "boots",
        "loafers",
        "derbies",
        "sneakers",
        "blazer",
        "overshirt",
        "knit",
        "sweater",
        "hoodie",
        "shorts",
        "bag",
        "belt",
        "scarf",
    }

    async def build(self, *, reasoning_input: FashionReasoningInput) -> FashionBrief:
        mode = reasoning_input.mode or "general_advice"
        structured = reasoning_input.structured_outfit_brief or {}
        if mode == "style_exploration":
            brief = self._build_style_exploration(reasoning_input, structured)
        elif mode == "garment_matching":
            brief = self._build_garment_matching(reasoning_input, structured)
        elif mode == "occasion_outfit":
            brief = self._build_occasion_outfit(reasoning_input, structured)
        else:
            brief = self._build_general_advice(reasoning_input)
        return self._inject_knowledge(brief=brief, reasoning_input=reasoning_input)

    def _build_style_exploration(
        self,
        reasoning_input: FashionReasoningInput,
        structured: dict[str, Any],
    ) -> FashionBrief:
        selected_style = structured.get("selected_style_direction") or reasoning_input.style_direction or {}
        style_identity = str(structured.get("style_identity") or selected_style.get("style_name") or "Style Direction").strip()
        style_family = self._optional_text(structured.get("style_family") or selected_style.get("style_family"))
        return FashionBrief(
            style_identity=style_identity,
            style_family=style_family,
            brief_mode="style_exploration",
            historical_reference=self._string_list(structured.get("historical_reference")),
            tailoring_logic=self._string_list(structured.get("tailoring_logic")),
            color_logic=self._string_list(structured.get("color_logic")),
            garment_list=self._string_list(structured.get("garment_list")),
            palette=self._string_list(structured.get("palette")),
            materials=self._string_list(structured.get("materials")),
            footwear=self._string_list(structured.get("footwear")),
            accessories=self._string_list(structured.get("accessories")),
            styling_notes=self._string_list(structured.get("styling_notes")),
            composition_rules=self._string_list(structured.get("composition_rules")),
            negative_constraints=self._string_list(structured.get("negative_constraints")),
            diversity_constraints=dict(structured.get("diversity_constraints") or reasoning_input.diversity_constraints),
            visual_preset=self._optional_text(structured.get("visual_preset") or selected_style.get("visual_preset")),
            generation_intent="style_exploration",
            knowledge_cards=list(reasoning_input.knowledge_cards),
            metadata={
                "style_id": selected_style.get("style_id"),
                "source_style_id": selected_style.get("style_id"),
                "style_summary": self._optional_text(structured.get("style_summary")),
                "composition_type": self._optional_text(structured.get("composition_type") or selected_style.get("composition_type")),
                "background_family": self._optional_text(structured.get("background_family") or selected_style.get("background_family")),
                "previous_style_directions": list(reasoning_input.previous_style_directions),
                "anti_repeat_constraints": dict(reasoning_input.anti_repeat_constraints),
                "semantic_constraints_hash": self._optional_text(structured.get("semantic_constraints_hash")),
                "visual_constraints_hash": self._optional_text(structured.get("visual_constraints_hash")),
                "diversity_constraints_hash": self._optional_text(structured.get("diversity_constraints_hash")),
                "knowledge_provider_used": reasoning_input.knowledge_provider_used,
            },
        )

    def _build_garment_matching(
        self,
        reasoning_input: FashionReasoningInput,
        structured: dict[str, Any],
    ) -> FashionBrief:
        anchor = structured.get("anchor_garment") or reasoning_input.anchor_garment or {}
        anchor_summary = self._optional_text(structured.get("anchor_summary")) or self._build_anchor_summary(anchor)
        palette = self._string_list([anchor.get("color_primary"), *(anchor.get("color_secondary") or [])])
        materials = self._string_list([anchor.get("material")])
        garment_list = self._string_list([anchor.get("garment_type"), *(structured.get("complementary_garments") or [])])
        return FashionBrief(
            style_identity=anchor_summary or "Anchor Garment Outfit",
            style_family=self._optional_text(anchor.get("category")),
            brief_mode="garment_matching",
            anchor_garment=anchor,
            historical_reference=self._string_list(structured.get("historical_reference")),
            tailoring_logic=self._string_list(structured.get("tailoring_notes")) + self._string_list(structured.get("silhouette_balance")),
            color_logic=self._string_list(structured.get("color_logic")),
            garment_list=garment_list,
            palette=palette,
            materials=materials,
            footwear=self._string_list(structured.get("footwear_options")),
            accessories=self._string_list(structured.get("accessories")),
            styling_notes=[self._optional_text(structured.get("styling_goal"))] if self._optional_text(structured.get("styling_goal")) else [],
            composition_rules=[
                "anchor garment centrality high",
                "build the outfit around the uploaded or described anchor item",
                *self._string_list(structured.get("image_prompt_notes")),
            ],
            negative_constraints=self._string_list(structured.get("negative_constraints"))
            + ["prevent style drift away from the anchor garment"],
            diversity_constraints=dict(reasoning_input.diversity_constraints),
            visual_preset=self._first_present(reasoning_input.visual_preset_candidates, default="editorial_studio"),
            generation_intent="garment_matching",
            knowledge_cards=list(reasoning_input.knowledge_cards),
            metadata={
                "anchor_summary": anchor_summary,
                "composition_type": "anchor-centered flat lay",
                "background_family": "studio",
                "knowledge_provider_used": reasoning_input.knowledge_provider_used,
            },
        )

    def _build_occasion_outfit(
        self,
        reasoning_input: FashionReasoningInput,
        structured: dict[str, Any],
    ) -> FashionBrief:
        occasion_context = structured.get("occasion_context") or reasoning_input.occasion_context or {}
        style_identity = self._optional_text(occasion_context.get("event_type")) or "Occasion Outfit"
        style_family = self._optional_text(occasion_context.get("dress_code") or occasion_context.get("desired_impression"))
        return FashionBrief(
            style_identity=style_identity,
            style_family=style_family,
            brief_mode="occasion_outfit",
            occasion_context=occasion_context,
            historical_reference=self._string_list(structured.get("historical_reference")),
            tailoring_logic=self._string_list(structured.get("tailoring_notes")) + self._string_list(structured.get("silhouette_logic")),
            color_logic=self._string_list(structured.get("color_logic")),
            garment_list=self._string_list(structured.get("garment_recommendations")),
            palette=self._string_list(occasion_context.get("color_preferences")),
            materials=self._extract_materials_from_notes(structured),
            footwear=self._string_list(structured.get("footwear_recommendations")),
            accessories=self._string_list(structured.get("accessories")),
            styling_notes=self._string_list(structured.get("comfort_notes")) + self._string_list(structured.get("impression_logic")),
            composition_rules=[
                "event suitability first",
                "dress code readability first",
                *self._string_list(structured.get("image_prompt_notes")),
            ],
            negative_constraints=self._string_list(structured.get("negative_constraints")),
            diversity_constraints=dict(reasoning_input.diversity_constraints),
            visual_preset=self._resolve_occasion_preset(occasion_context),
            generation_intent="occasion_outfit",
            knowledge_cards=list(reasoning_input.knowledge_cards),
            metadata={
                "composition_type": "occasion-led flat lay",
                "background_family": "editorial surface",
                "knowledge_provider_used": reasoning_input.knowledge_provider_used,
            },
        )

    def _build_general_advice(self, reasoning_input: FashionReasoningInput) -> FashionBrief:
        image_brief = self._optional_text(reasoning_input.image_brief_en) or "editorial outfit"
        style_seed = reasoning_input.style_seed or {}
        style_identity = self._optional_text(style_seed.get("title")) or self._derive_style_identity(reasoning_input)
        return FashionBrief(
            style_identity=style_identity,
            style_family=self._optional_text(style_seed.get("slug")),
            brief_mode="general_advice",
            garment_list=self._extract_matching_tokens(image_brief, self.GARMENT_TOKENS),
            palette=self._extract_matching_tokens(image_brief, self.COLOR_TOKENS),
            materials=self._extract_matching_tokens(image_brief, self.MATERIAL_TOKENS),
            styling_notes=[self._optional_text(reasoning_input.recommendation_text)] if self._optional_text(reasoning_input.recommendation_text) else [],
            composition_rules=["lighter composition constraints for explanatory generation"],
            diversity_constraints=dict(reasoning_input.diversity_constraints),
            visual_preset=self._first_present(reasoning_input.visual_preset_candidates, default="editorial_studio"),
            generation_intent="general_advice",
            knowledge_cards=list(reasoning_input.knowledge_cards),
            metadata={
                "style_id": self._optional_text(style_seed.get("slug")),
                "source_style_id": self._optional_text(style_seed.get("slug")),
                "composition_type": "editorial flat lay",
                "background_family": "studio",
                "knowledge_provider_used": reasoning_input.knowledge_provider_used,
            },
        )

    def _inject_knowledge(self, *, brief: FashionBrief, reasoning_input: FashionReasoningInput) -> FashionBrief:
        bundle = self._parse_bundle(reasoning_input.knowledge_bundle)
        historical_reference = list(brief.historical_reference)
        tailoring_logic = list(brief.tailoring_logic)
        color_logic = list(brief.color_logic)
        materials = list(brief.materials)
        garment_list = list(brief.garment_list)
        palette = list(brief.palette)
        composition_rules = list(brief.composition_rules)
        negative_constraints = list(brief.negative_constraints)
        metadata = dict(brief.metadata)
        style_identity = brief.style_identity
        style_family = brief.style_family
        if bundle is not None:
            primary_style = bundle.style_cards[0] if bundle.style_cards else None
            if primary_style is not None:
                if not metadata.get("style_id"):
                    metadata["style_id"] = primary_style.style_id
                if not metadata.get("source_style_id"):
                    metadata["source_style_id"] = primary_style.style_id
                metadata["style_catalog_summary"] = primary_style.summary
                if not style_identity or style_identity in {"Style Direction", "Stylist Direction"}:
                    style_identity = primary_style.title
                if style_family is None:
                    style_family = self._optional_text(primary_style.metadata.get("canonical_name"))
                for item in primary_style.metadata.get("palette", []):
                    if self._optional_text(item) and item not in palette:
                        palette.append(item)
                for item in primary_style.metadata.get("hero_garments", []):
                    if self._optional_text(item) and item not in garment_list:
                        garment_list.append(item)
                for item in primary_style.metadata.get("negative_constraints", []):
                    cleaned = self._optional_text(item)
                    if cleaned and cleaned not in negative_constraints:
                        negative_constraints.append(cleaned)
            historical_reference = self._merge_card_texts(historical_reference, bundle.history_cards, limit=5)
            tailoring_logic = self._merge_card_texts(tailoring_logic, bundle.tailoring_cards, limit=6)
            color_logic = self._merge_card_texts(color_logic, bundle.color_cards, limit=6)
            composition_rules = self._merge_card_texts(composition_rules, bundle.flatlay_cards, limit=6)
            materials = self._merge_materials(materials, bundle.materials_cards)
            metadata.update(bundle.retrieval_trace)
            metadata["knowledge_refs"] = bundle.knowledge_refs()
        for card in reasoning_input.knowledge_cards:
            key = str(card.get("key") or "").strip().lower()
            text = self._optional_text(card.get("text"))
            if not text:
                continue
            if key in {"history", "historical", "diversity"} and text not in historical_reference:
                historical_reference.append(text)
            if key in {"proportion", "clarity", "tailoring"} and text not in tailoring_logic:
                tailoring_logic.append(text)
            if key in {"color", "palette"} and text not in color_logic:
                color_logic.append(text)
            if key in {"materials", "fabric"}:
                for material in self._extract_matching_tokens(text, self.MATERIAL_TOKENS):
                    if material not in materials:
                        materials.append(material)
        return brief.model_copy(
            update={
                "style_identity": style_identity,
                "style_family": style_family,
                "historical_reference": historical_reference[:4],
                "tailoring_logic": tailoring_logic[:5],
                "color_logic": color_logic[:5],
                "garment_list": garment_list[:8],
                "palette": palette[:6],
                "materials": materials[:6],
                "composition_rules": composition_rules[:6],
                "negative_constraints": negative_constraints[:8],
                "metadata": metadata,
            }
        )

    def _parse_bundle(self, payload: dict[str, Any] | None) -> KnowledgeBundle | None:
        if not isinstance(payload, dict):
            return None
        try:
            return KnowledgeBundle.model_validate(payload)
        except Exception:
            return None

    def _merge_card_texts(self, existing: list[str], cards: list[Any], *, limit: int) -> list[str]:
        result = list(existing)
        seen = {item.lower() for item in existing if isinstance(item, str)}
        for card in cards:
            summary = self._optional_text(getattr(card, "summary", None))
            if summary and summary.lower() not in seen:
                seen.add(summary.lower())
                result.append(summary)
            body = self._optional_text(getattr(card, "body", None))
            if body and body.lower() not in seen:
                seen.add(body.lower())
                result.append(body)
            if len(result) >= limit:
                break
        return result[:limit]

    def _merge_materials(self, existing: list[str], cards: list[Any]) -> list[str]:
        result = list(existing)
        seen = {item.lower() for item in existing if isinstance(item, str)}
        for card in cards:
            metadata = getattr(card, "metadata", {}) or {}
            for value in metadata.get("materials", []):
                cleaned = self._optional_text(value)
                if not cleaned or cleaned.lower() in seen:
                    continue
                seen.add(cleaned.lower())
                result.append(cleaned)
            for value in self._extract_matching_tokens(getattr(card, "compact_text", lambda: "")(), self.MATERIAL_TOKENS):
                if value.lower() in seen:
                    continue
                seen.add(value.lower())
                result.append(value)
        return result[:6]

    def _derive_style_identity(self, reasoning_input: FashionReasoningInput) -> str:
        recommendation = self._optional_text(reasoning_input.recommendation_text)
        if recommendation:
            return recommendation.split(".")[0].strip()[:80] or "Stylist Direction"
        user_message = self._optional_text(reasoning_input.user_message)
        if user_message:
            return user_message[:80]
        return "Stylist Direction"

    def _extract_matching_tokens(self, text: str, vocabulary: set[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for raw_token in text.replace(",", " ").replace(";", " ").split():
            token = raw_token.strip(" .:!?'\"()[]").lower()
            if not token or token not in vocabulary or token in seen:
                continue
            seen.add(token)
            result.append(token)
        return result

    def _extract_materials_from_notes(self, structured: dict[str, Any]) -> list[str]:
        notes = " ".join(
            self._string_list(structured.get("comfort_notes"))
            + self._string_list(structured.get("outerwear_notes"))
        )
        return self._extract_matching_tokens(notes.lower(), self.MATERIAL_TOKENS)

    def _build_anchor_summary(self, anchor: dict[str, Any]) -> str | None:
        bits = [anchor.get("color_primary"), anchor.get("material"), anchor.get("garment_type"), anchor.get("fit")]
        summary = " ".join(str(bit).strip() for bit in bits if self._optional_text(bit))
        return summary or None

    def _resolve_occasion_preset(self, occasion_context: dict[str, Any]) -> str:
        dress_code = self._optional_text(occasion_context.get("dress_code"))
        if dress_code in {"formal", "black tie", "cocktail"}:
            return "editorial_studio"
        if self._optional_text(occasion_context.get("event_type")) == "exhibition":
            return "dark_gallery"
        return "airy_catalog"

    def _first_present(self, values: list[str], *, default: str) -> str:
        for value in values:
            cleaned = self._optional_text(value)
            if cleaned:
                return cleaned
        return default

    def _optional_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        cleaned = value.strip()
        return cleaned or None

    def _string_list(self, values: Any) -> list[str]:
        if values is None:
            return []
        if isinstance(values, str):
            values = [values]
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = self._optional_text(value)
            lowered = cleaned.lower() if cleaned else ""
            if not cleaned or lowered in seen:
                continue
            seen.add(lowered)
            result.append(cleaned)
        return result
