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
            occasion_summary=self._occasion_summary(occasion_context),
            styling_goal=styling_goal,
            dressing_rules=[item.text for item in knowledge_result.items[:3]],
            silhouette_notes=self._silhouette_notes(occasion_context),
            palette_direction=self._palette_direction(occasion_context),
            layering_notes=self._layering_notes(occasion_context),
            footwear_guidance=self._footwear_guidance(occasion_context),
            weather_notes=self._weather_notes(occasion_context),
            etiquette_notes=self._etiquette_notes(occasion_context),
            image_prompt_notes=[
                "Luxury editorial flat lay, garments only, polished and event-aware.",
                "One complete outfit only with clear hierarchy, no clutter, no human model.",
            ],
        )

    def compile(self, outfit_brief: OccasionOutfitBrief) -> dict[str, Any]:
        return {
            "brief_type": "occasion_outfit",
            "occasion_summary": outfit_brief.occasion_summary,
            "occasion_context": outfit_brief.occasion_context.model_dump(exclude_none=True),
            "styling_goal": outfit_brief.styling_goal,
            "dressing_rules": outfit_brief.dressing_rules,
            "silhouette_notes": outfit_brief.silhouette_notes,
            "palette_direction": outfit_brief.palette_direction,
            "layering_notes": outfit_brief.layering_notes,
            "footwear_guidance": outfit_brief.footwear_guidance,
            "weather_notes": outfit_brief.weather_notes,
            "etiquette_notes": outfit_brief.etiquette_notes,
            "image_prompt_notes": outfit_brief.image_prompt_notes,
        }

    def _occasion_summary(self, occasion_context: OccasionContext) -> str:
        parts = [
            occasion_context.event_type,
            occasion_context.location,
            occasion_context.time_of_day,
            occasion_context.season,
            occasion_context.dress_code or occasion_context.desired_impression,
        ]
        return ", ".join(str(part).strip() for part in parts if part) or "occasion outfit"

    def _silhouette_notes(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.dress_code in {"black tie", "formal", "cocktail"}:
            return ["Keep the silhouette polished, elongated, and sharply edited."]
        if occasion_context.desired_impression == "relaxed":
            return ["Use one relaxed layer balanced by one cleaner structured piece."]
        return ["Keep the silhouette coherent and appropriate for the event formality."]

    def _palette_direction(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Anchor the palette in refined neutrals and add one intentional accent if needed."]
        if occasion_context.color_preferences:
            notes.append(f"Honor the preferred colors: {', '.join(occasion_context.color_preferences[:3])}.")
        if occasion_context.desired_impression == "bold":
            notes.append("Allow one stronger accent color without overwhelming the whole outfit.")
        return notes

    def _layering_notes(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.weather_context in {"cold", "rainy", "windy"}:
            return ["Add an outer layer that keeps polish consistent with the event."]
        if occasion_context.season == "summer":
            return ["Keep layering light and breathable so the outfit stays sharp but not heavy."]
        return ["Use layers only when they support polish, readability, and occasion appropriateness."]

    def _footwear_guidance(self, occasion_context: OccasionContext) -> list[str]:
        if occasion_context.dress_code in {"black tie", "formal"}:
            return ["Choose polished dress shoes or the cleanest formal footwear available."]
        if occasion_context.location == "outdoor":
            return ["Choose stable footwear that still respects the event polish level."]
        return ["Use footwear to confirm the event formality rather than compete with the outfit."]

    def _weather_notes(self, occasion_context: OccasionContext) -> list[str]:
        notes: list[str] = []
        if occasion_context.weather_context:
            notes.append(f"Adapt fabrics and layers to {occasion_context.weather_context} conditions.")
        if occasion_context.season:
            notes.append(f"Keep materials and layering weight aligned with {occasion_context.season}.")
        return notes

    def _etiquette_notes(self, occasion_context: OccasionContext) -> list[str]:
        notes = ["Respect the event dress code before adding personality through texture or accessories."]
        if occasion_context.event_type == "wedding":
            notes.append("Keep the look celebratory and polished without visually competing with the hosts.")
        if occasion_context.event_type == "conference":
            notes.append("Keep the look sharp, mobile, and professional throughout the day.")
        return notes
