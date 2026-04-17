import type { CommandName } from "@/entities/command/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import type { StyleDirectionEntity } from "@/entities/style-direction/model/types";
import type { ChatMode, ChatModeContext, ClarificationKind, FlowState } from "@/shared/api/types";

export interface FrontendScenarioContext {
  activeMode: ChatMode;
  flowState: FlowState;
  pendingClarification: boolean;
  pendingClarificationText: string | null;
  clarificationKind: ClarificationKind | null;
  currentJobId: string | null;
  currentStyleId: string | null;
  currentStyleName: string | null;
  styleHistory: StyleDirectionEntity[];
  commandName: CommandName | null;
  canSendFreeformMessage: boolean;
  canAttachAsset: boolean;
  visualizationOffer: VisualizationOfferState;
  rawContext: ChatModeContext;
}
