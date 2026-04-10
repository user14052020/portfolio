import type { ChatResponse } from "@/entities/chat-session/model/types";
import { submitFollowupClarification } from "@/features/followup-clarification/model/submitFollowupClarification";
import type { Locale } from "@/shared/api/types";

export async function sendGarmentFollowup({
  sessionId,
  locale,
  message,
  assetId = null,
  clientMessageId,
}: {
  sessionId: string;
  locale: Locale;
  message: string | null;
  assetId?: number | string | null;
  clientMessageId?: string;
}): Promise<ChatResponse> {
  return submitFollowupClarification({
    sessionId,
    locale,
    message,
    assetId,
    clientMessageId,
  });
}
