from typing import Any

from app.application.stylist_chat.contracts.ports import KnowledgeResult, OccasionOutfitBriefBuilder
from app.domain.occasion_outfit.entities.occasion_context import OccasionContext
from app.domain.occasion_outfit.entities.occasion_outfit_brief import OccasionOutfitBrief


class OccasionBriefCompiler(OccasionOutfitBriefBuilder):
    async def build(
        self,
        occasion_context: OccasionContext,
        context: dict[str, Any],
        knowledge_result: KnowledgeResult,
    ) -> OccasionOutfitBrief:
        event_label = occasion_context.event_type or "event"
        styling_goal = (
            f"Build an event-aware outfit for a {event_label} that respects formality, timing, season, and the user's desired impression."
        )
        return OccasionOutfitBrief(
            occasion_context=occasion_context,
            styling_goal=styling_goal,
            dress_code_logic=self._dress_code_logic(occasion_context, knowledge_result),
            impression_logic=self._impression_logic(occasion_context),
            color_logic=self._color_logic(occasion_context),
            silhouette_logic=self._silhouette_logic(occasion_context),
            garment_recommendations=self._garment_recommendations(occasion_context),
            footwear_recommendations=self._footwear_recommendations(occasion_context),
            accessories=self._accessories(occasion_context),
            outerwear_notes=self._outerwear_notes(occasion_context),
            comfort_notes=self._comfort_notes(occasion_context),
            historical_reference=self._historical_reference(occasion_context),
            tailoring_notes=self._tailoring_notes(occasion_context),
            negative_constraints=self._negative_constraints(occasion_context),
            image_prompt_notes=[
                "Luxury editorial flat lay, garments only, polished and event-aware.",
                "One complete outfit only with clear hierarchy, no clutter, no human model.",
            ],
        )

    def compile(self, outfit_brief: OccasionOutfitBrief) -> dict[str, Any]:
        return {
            "brief_type": "occasion_outfit",
            "occasion_context": outfit_brief.occasion_context.model_dump(exclude_none=True),
            "styling_goal": outfit_brief.styling_goal,
            "dress_code_logic": outfit_brief.dress_code_logic,
            "impression_logic": outfit_brief.impression_logic,
            "color_logic": outfit_brief.color_logic,
            "silhouette_logic": outfit_brief.silhouette_logic,
            "garment_recommendations": outfit_brief.garment_recommendations,
            "footwear_recommendations": outfit_brief.footwear_recommendations,
            "accessories": outfit_brief.accessories,
            "outerwear_notes": outfit_brief.outerwear_notes,
            "comfort_notes": outfit_brief.comfort_notes,
            "historical_reference": outfit_brief.historical_reference,
            "tailoring_notes": outfit_brief.tailoring_notes,
            "negative_constraints": outfit_brief.negative_constraints,
            "image_prompt_notes": outfit_brief.image_prompt_notes,
        }

    def _dress_code_logic(
        self,
        occasion_context: OccasionContext,
        knowledge_result: KnowledgeResult,
    ) -> list[str]:
        logic = [item.text for item in knowledge_result.items[:2]]
        if occasion_context.dress_code:
            logic.insert(0, f"Honor the {occasion_context.dress_code} dress code before adding personality.")
        elif occasion_context.desired_impression:
            logic.insert(0, "Use the event formality as the base line and layer personality on top of it.")
        return logic[:3]

    def _impression_logic(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.desired_impression == "bold":
            return ["Make one focal point feel bold while the rest of the outfit stays clean and deliberate."]
        if occasion_context.desired_impression == "relaxed":
            return ["Keep the mood relaxed through softer structure, but do not let the outfit look careless."]
        if occasion_context.desired_impression:
            return [f"Translate the desired impression '{occasion_context.desired_impression}' into silhouette, texture, and finishing details."]
        return ["Let the outfit feel event-appropriate first, then add subtle personality through texture or accessories."]

    def _color_logic(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Anchor the palette in refined neutrals and add one intentional accent if needed."]
        if occasion_context.color_preferences:
            notes.append(f"Honor the preferred colors: {', '.join(occasion_context.color_preferences[:3])}.")
        if occasion_context.desired_impression == "bold":
            notes.append("Allow one stronger accent color without overwhelming the whole outfit.")
        return notes

    def _silhouette_logic(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.dress_code in {"black tie", "formal", "cocktail"}:
            return ["Keep the silhouette polished, elongated, and sharply edited."]
        if occasion_context.desired_impression == "relaxed":
            return ["Use one relaxed layer balanced by one cleaner structured piece."]
        return ["Keep the silhouette coherent and appropriate for the event formality."]

    def _garment_recommendations(self, occasion_context: OccasionContext) -> list[str]:
        recommendations = ["Build one complete outfit with a clear hero layer, a clean base, and one supporting accent."]
        if occasion_context.dress_code in {"black tie", "formal"}:
            recommendations.append("Lean into tailored garments with crisp finishing and minimal casual disruption.")
        elif occasion_context.dress_code == "smart casual":
            recommendations.append("Balance one tailored garment with one relaxed counterpart so the outfit stays readable.")
        if occasion_context.event_type == "exhibition":
            recommendations.append("Favor quietly expressive pieces that feel thoughtful rather than overdone.")
        return recommendations[:3]

    def _footwear_recommendations(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.dress_code in {"black tie", "formal"}:
            return ["Choose polished dress shoes or the cleanest formal footwear available."]
        if occasion_context.location == "outdoor":
            return ["Choose stable footwear that still respects the event polish level."]
        return ["Use footwear to confirm the event formality rather than compete with the outfit."]

    def _accessories(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Keep accessories edited and let them support the event mood instead of stealing attention."]
        if occasion_context.desired_impression == "bold":
            notes.append("Use one sharper accessory as a focal point and keep the rest restrained.")
        return notes[:2]

    def _outerwear_notes(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.weather_context in {"cold", "rainy", "windy"}:
            return ["Add an outer layer that keeps polish consistent with the event."]
        if occasion_context.season == "summer":
            return ["Keep layering light and breathable so the outfit stays sharp but not heavy."]
        return ["Use layers only when they support polish, readability, and occasion appropriateness."]

    def _comfort_notes(self, occasion_context: OccasionContext) -> list[str]:
        notes: list[str] = []
        if occasion_context.comfort_requirements:
            notes.append(f"Keep comfort requirements visible: {', '.join(occasion_context.comfort_requirements[:2])}.")
        if occasion_context.weather_context:
            notes.append(f"Adapt fabrics and layers to {occasion_context.weather_context} conditions.")
        if occasion_context.season:
            notes.append(f"Keep materials and layering weight aligned with {occasion_context.season}.")
        return notes

    def _historical_reference(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.event_type == "theater":
            return ["Borrow from classic evening polish with clean lines and a composed silhouette."]
        if occasion_context.event_type == "exhibition":
            return ["Reference gallery-ready refinement: modern, intelligent, and visually edited."]
        return ["Keep the visual language timeless enough to survive the event photographs."]

    def _tailoring_notes(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Respect the event dress code before adding personality through texture or accessories."]
        if occasion_context.dress_code in {"formal", "black tie", "cocktail"}:
            notes.append("Keep fit lines clean and intentional so the outfit reads polished from a distance.")
        if occasion_context.event_type == "conference":
            notes.append("Keep the look sharp, mobile, and professional throughout the day.")
        return notes

    def _negative_constraints(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Do not underdress the event relative to its stated formality."]
        if occasion_context.desired_impression == "bold":
            notes.append("Do not make every garment loud at once.")
        if occasion_context.event_type == "wedding":
            notes.append("Do not visually compete with the hosts or ceremonial focal points.")
        return notes
