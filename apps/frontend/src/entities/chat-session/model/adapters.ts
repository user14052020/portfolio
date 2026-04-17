import type { ChatResponse } from "@/entities/chat-session/model/types";
import { adaptFrontendScenarioContext } from "@/entities/stylist-context/model/adapters";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import type { StylistMessageResponse } from "@/shared/api/types";

export function adaptChatResponse(response: StylistMessageResponse): ChatResponse {
  const context = adaptFrontendScenarioContext(response.session_context);
  const replyText = response.decision.text_reply ?? response.recommendation_text ?? null;
  const jobId = response.decision.job_id ?? response.generation_job?.public_id ?? null;
  const visualizationOffer: VisualizationOfferState = {
    canOfferVisualization: Boolean(response.decision.can_offer_visualization),
    ctaText: response.decision.cta_text ?? null,
    visualizationType: response.decision.visualization_type ?? null,
  };
  const base = {
    sessionId: response.session_id,
    assistantMessage: {
      ...response.assistant_message,
      generation_job: response.generation_job ?? response.assistant_message.generation_job ?? null,
    },
    generationJob: response.generation_job ?? null,
    timestamp: response.timestamp,
    activeMode: response.decision.active_mode,
    flowState: response.decision.flow_state,
    context,
    visualizationOffer,
  } as const;

  switch (response.decision.decision_type) {
    case "clarification_required":
      return {
        ...base,
        decisionType: "clarification_required",
        replyText: replyText ?? "",
        clarificationKind: context.clarificationKind,
        jobId: null,
      };
    case "text_and_generate":
      return {
        ...base,
        decisionType: "text_and_generate",
        replyText: replyText ?? "",
        jobId,
      };
    case "generation_only":
      return {
        ...base,
        decisionType: "generation_only",
        replyText: null,
        jobId,
      };
    case "error_recoverable":
    case "error_hard":
      return {
        ...base,
        decisionType: response.decision.decision_type,
        replyText: replyText ?? "",
        jobId: null,
      };
    case "text_only":
    default:
      return {
        ...base,
        decisionType: "text_only",
        replyText: replyText ?? "",
        jobId: null,
      };
  }
}
