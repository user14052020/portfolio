import type { CommandName } from "@/entities/command/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import type { ChatModeContext } from "@/shared/api/types";

import type { FrontendScenarioContext } from "./types";

function normalizeCommandName(rawValue: string | null | undefined, activeMode: ChatModeContext["active_mode"]): CommandName | null {
  if (
    rawValue === "garment_matching" ||
    rawValue === "style_exploration" ||
    rawValue === "occasion_outfit"
  ) {
    return rawValue;
  }

  if (
    activeMode === "garment_matching" ||
    activeMode === "style_exploration" ||
    activeMode === "occasion_outfit"
  ) {
    return activeMode;
  }

  return null;
}

export function adaptFrontendScenarioContext(rawContext: ChatModeContext): FrontendScenarioContext {
  const visualizationOffer: VisualizationOfferState = {
    canOfferVisualization: Boolean(rawContext.visualization_offer?.can_offer_visualization),
    ctaText: rawContext.visualization_offer?.cta_text ?? null,
    visualizationType: rawContext.visualization_offer?.visualization_type ?? null,
  };
  return {
    activeMode: rawContext.active_mode,
    flowState: rawContext.flow_state,
    pendingClarification: Boolean(rawContext.pending_clarification),
    pendingClarificationText: rawContext.pending_clarification ?? null,
    clarificationKind: rawContext.clarification_kind ?? null,
    currentJobId: rawContext.current_job_id ?? null,
    currentStyleId: rawContext.current_style_id ?? null,
    currentStyleName: rawContext.current_style_name ?? null,
    styleHistory: rawContext.style_history,
    commandName: normalizeCommandName(
      rawContext.command_context?.command_name,
      rawContext.active_mode
    ),
    canSendFreeformMessage: true,
    canAttachAsset: true,
    visualizationOffer,
    rawContext,
  };
}
