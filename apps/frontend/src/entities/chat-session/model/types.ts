import type { GenerationJobState } from "@/entities/generation-job/model/types";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import type { ChatMessage, ChatMode, ClarificationKind, DecisionType, FlowState } from "@/shared/api/types";

interface ChatResponseBase {
  sessionId: string;
  assistantMessage: ChatMessage;
  generationJob: GenerationJobState | null;
  timestamp: string;
  activeMode: ChatMode;
  flowState: FlowState;
  context: FrontendScenarioContext;
  visualizationOffer: VisualizationOfferState;
}

export type ChatResponse =
  | (ChatResponseBase & {
      decisionType: "text_only";
      replyText: string;
      jobId: null;
    })
  | (ChatResponseBase & {
      decisionType: "clarification_required";
      replyText: string;
      clarificationKind: ClarificationKind | null;
      jobId: null;
    })
  | (ChatResponseBase & {
      decisionType: "text_and_generate";
      replyText: string;
      jobId: string | null;
    })
  | (ChatResponseBase & {
      decisionType: "generation_only";
      replyText: null;
      jobId: string | null;
    })
  | (ChatResponseBase & {
      decisionType: "error_recoverable" | "error_hard";
      replyText: string;
      jobId: null;
    });

export interface ChatDecisionSnapshot {
  decisionType: DecisionType;
  activeMode: ChatMode;
  flowState: FlowState;
  replyText: string | null;
  jobId: string | null;
}
