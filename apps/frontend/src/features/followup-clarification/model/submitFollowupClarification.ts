import type { ChatResponse } from "@/entities/chat-session/model/types";
import {
  buildFollowupMessagePayload,
  sendFollowupMessage,
} from "@/features/send-chat-message/model/sendChatMessage";
import type { Locale } from "@/shared/api/types";

export async function submitFollowupClarification({
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
  return sendFollowupMessage(
    buildFollowupMessagePayload({
      sessionId,
      locale,
      message,
      assetId,
      clientMessageId,
    })
  );
}
