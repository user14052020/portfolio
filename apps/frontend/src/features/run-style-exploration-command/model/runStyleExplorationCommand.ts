import type { ChatResponse } from "@/entities/chat-session/model/types";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
  runQuickActionCommand,
} from "@/features/run-chat-command/model/runChatCommand";
import type { Locale } from "@/shared/api/types";

export async function runStyleExplorationCommand({
  sessionId,
  locale,
  clientMessageId,
}: {
  sessionId: string;
  locale: Locale;
  clientMessageId?: string;
}): Promise<ChatResponse> {
  const action = getQuickActionDefinitions(locale).find((item) => item.id === "style_exploration");
  if (!action) {
    throw new Error("Style exploration quick action is not configured.");
  }

  return runQuickActionCommand(
    buildQuickActionCommandPayload({
      sessionId,
      locale,
      action,
      assetId: null,
      clientMessageId,
    })
  );
}
