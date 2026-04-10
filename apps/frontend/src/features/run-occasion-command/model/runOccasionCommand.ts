import type { ChatResponse } from "@/entities/chat-session/model/types";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
  runQuickActionCommand,
} from "@/features/run-chat-command/model/runChatCommand";
import type { Locale } from "@/shared/api/types";

export async function runOccasionCommand({
  sessionId,
  locale,
  assetId = null,
  clientMessageId,
}: {
  sessionId: string;
  locale: Locale;
  assetId?: number | string | null;
  clientMessageId?: string;
}): Promise<ChatResponse> {
  const action = getQuickActionDefinitions(locale).find((item) => item.id === "occasion_outfit");
  if (!action) {
    throw new Error("Occasion outfit quick action is not configured.");
  }

  return runQuickActionCommand(
    buildQuickActionCommandPayload({
      sessionId,
      locale,
      action,
      assetId,
      clientMessageId,
    })
  );
}
