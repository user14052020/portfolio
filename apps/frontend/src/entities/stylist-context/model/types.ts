import type { CommandName } from "@/entities/command/model/types";
import type { ChatMode, ChatModeContext, ClarificationKind, FlowState } from "@/shared/api/types";

export interface FrontendScenarioContext {
  activeMode: ChatMode;
  flowState: FlowState;
  pendingClarification: boolean;
  pendingClarificationText: string | null;
  clarificationKind: ClarificationKind | null;
  currentJobId: string | null;
  commandName: CommandName | null;
  canSendFreeformMessage: boolean;
  canAttachAsset: boolean;
  rawContext: ChatModeContext;
}
