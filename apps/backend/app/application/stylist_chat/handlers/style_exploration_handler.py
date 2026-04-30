from typing import Any

from app.application.stylist_chat.contracts.command import ChatCommand
from app.application.stylist_chat.contracts.ports import ContextCheckpointWriter
from app.application.stylist_chat.results.decision_result import DecisionResult
from app.application.stylist_chat.use_cases.build_diversity_constraints import BuildDiversityConstraintsUseCase
from app.application.stylist_chat.use_cases.build_style_exploration_brief import BuildStyleExplorationBriefUseCase
from app.application.stylist_chat.use_cases.persist_style_direction import PersistStyleDirectionUseCase
from app.application.stylist_chat.use_cases.select_candidate_style import SelectCandidateStyleUseCase
from app.application.stylist_chat.use_cases.start_style_exploration import StartStyleExplorationUseCase
from app.domain.chat_context import ChatModeContext
from app.domain.state_machine.style_exploration_machine import StyleExplorationStateMachine

from .base import BaseChatModeHandler


class StyleExplorationHandler(BaseChatModeHandler):
    def __init__(
        self,
        *,
        start_use_case: StartStyleExplorationUseCase,
        select_candidate_style_use_case: SelectCandidateStyleUseCase,
        build_diversity_constraints_use_case: BuildDiversityConstraintsUseCase,
        build_style_exploration_brief_use_case: BuildStyleExplorationBriefUseCase,
        persist_style_direction_use_case: PersistStyleDirectionUseCase,
        style_history_service,
        style_history_provider,
        context_checkpoint_writer: ContextCheckpointWriter | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.start_use_case = start_use_case
        self.select_candidate_style_use_case = select_candidate_style_use_case
        self.build_diversity_constraints_use_case = build_diversity_constraints_use_case
        self.build_style_exploration_brief_use_case = build_style_exploration_brief_use_case
        self.persist_style_direction_use_case = persist_style_direction_use_case
        self.style_history_service = style_history_service
        self.style_history_provider = style_history_provider
        self.context_checkpoint_writer = context_checkpoint_writer

    async def handle(
        self,
        *,
        command: ChatCommand,
        context: ChatModeContext,
    ) -> DecisionResult:
        self.start_use_case.execute(context=context)
        selection = await self.select_candidate_style_use_case.execute(
            session_id=command.session_id,
            current_history=context.style_history,
        )
        context.style_history = selection.history

        previous_style_directions = self.style_history_service.to_prompt_items(selection.history)
        diversity_constraints = self.build_diversity_constraints_use_case.execute(
            history=selection.history,
            candidate_style=selection.candidate_style,
            session_context={"session_id": command.session_id},
        )
        if selection.source_model is not None:
            await self.style_history_provider.record_exposure(
                session_id=command.session_id,
                style_direction=selection.source_model,
            )

        StyleExplorationStateMachine.mark_ready_for_generation(context)
        style_brief = await self.build_style_exploration_brief_use_case.execute(
            style_direction=selection.candidate_style,
            history=selection.history,
            diversity_constraints=diversity_constraints,
        )
        resolved_style_direction = style_brief.selected_style_direction
        self.persist_style_direction_use_case.execute(
            context=context,
            style_direction=resolved_style_direction,
        )
        if self.context_checkpoint_writer is not None:
            await self.context_checkpoint_writer.save_checkpoint(
                session_id=command.session_id,
                context=context,
            )
        effective_command = command
        if not command.normalized_message():
            effective_command = command.model_copy(
                update={"message": "Новый стиль" if command.locale == "ru" else "Try another style"}
            )

        decision = await self.run_reasoning(
            command=effective_command,
            context=context,
            must_generate=True,
            style_seed=self.style_seed_from_context(selection.candidate_style),
            previous_style_directions=previous_style_directions,
            occasion_context=None,
            anti_repeat_constraints=diversity_constraints.to_reasoning_dict(),
            knowledge_mode="style_exploration",
            style_history_used=bool(previous_style_directions),
            structured_outfit_brief=style_brief.to_prompt_payload(),
        )
        style_context_patch = {
            "previous_style_directions": previous_style_directions,
            "diversity_constraints": diversity_constraints.model_dump(mode="json"),
            "style_exploration_brief": style_brief.to_prompt_payload(),
        }
        decision.context_patch.update(style_context_patch)
        self._apply_style_telemetry(
            decision=decision,
            candidate_style=resolved_style_direction,
            history=context.style_history,
            diversity_constraints=diversity_constraints.to_reasoning_dict(),
        )
        context.last_generated_outfit_summary = decision.text_reply
        if decision.generation_payload is not None:
            context.last_generation_prompt = decision.generation_payload.prompt
        decision.context_patch.update(style_context_patch)
        return decision

    def _apply_style_telemetry(
        self,
        *,
        decision: DecisionResult,
        candidate_style,
        history,
        diversity_constraints: dict[str, object],
    ) -> None:
        latest_previous = history[-2] if len(history) >= 2 else None
        decision.telemetry.update(
            {
                "style_id": candidate_style.style_id,
                "style_name": candidate_style.style_name,
                "style_history_size": len(history),
                "palette": list(candidate_style.palette),
                "hero_garments": list(candidate_style.hero_garments),
                "composition_type": candidate_style.composition_type,
                "visual_preset": candidate_style.visual_preset,
                "semantic_constraints_hash": diversity_constraints.get("semantic_constraints_hash"),
                "visual_constraints_hash": diversity_constraints.get("visual_constraints_hash"),
                "semantic_diversity_score": self._semantic_diversity_score(candidate_style, history[:-1]),
                "visual_diversity_score": self._visual_diversity_score(candidate_style, history[:-1]),
                "palette_repeat_rate": self._repeat_rate(candidate_style.palette, latest_previous.palette if latest_previous else []),
                "hero_garment_repeat_rate": self._repeat_rate(
                    candidate_style.hero_garments,
                    latest_previous.hero_garments if latest_previous else [],
                ),
                "silhouette_repeat_rate": (
                    1.0
                    if latest_previous is not None
                    and candidate_style.silhouette_family == latest_previous.silhouette_family
                    else 0.0
                ),
                "composition_repeat_rate": (
                    1.0
                    if latest_previous is not None
                    and candidate_style.composition_type == latest_previous.composition_type
                    else 0.0
                ),
            }
        )

    def _semantic_diversity_score(self, candidate_style, previous_history) -> float:
        if not previous_history:
            return 1.0
        latest = previous_history[-1]
        score = 0.0
        if set(candidate_style.palette).isdisjoint(set(latest.palette)):
            score += 0.35
        if set(candidate_style.hero_garments).isdisjoint(set(latest.hero_garments)):
            score += 0.35
        if candidate_style.silhouette_family != latest.silhouette_family:
            score += 0.3
        return round(min(score, 1.0), 3)

    def _visual_diversity_score(self, candidate_style, previous_history) -> float:
        if not previous_history:
            return 1.0
        latest = previous_history[-1]
        score = 0.0
        if candidate_style.composition_type != latest.composition_type:
            score += 0.4
        if candidate_style.background_family != latest.background_family:
            score += 0.3
        if candidate_style.visual_preset != latest.visual_preset:
            score += 0.3
        return round(min(score, 1.0), 3)

    def _repeat_rate(self, current_values, previous_values) -> float:
        current = {value.strip().lower() for value in current_values if isinstance(value, str) and value.strip()}
        previous = {value.strip().lower() for value in previous_values if isinstance(value, str) and value.strip()}
        if not current or not previous:
            return 0.0
        return round(len(current & previous) / len(current), 3)
