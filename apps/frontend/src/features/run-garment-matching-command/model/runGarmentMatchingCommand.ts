import type { ChatResponse } from "@/entities/chat-session/model/types";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
  runQuickActionCommand,
} from "@/features/run-chat-command/model/runChatCommand";
import type { Locale } from "@/shared/api/types";

export async function runGarmentMatchingCommand({
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
  const action = getQuickActionDefinitions(locale).find((item) => item.id === "garment_matching");
  if (!action) {
    throw new Error("Garment matching quick action is not configured.");
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
