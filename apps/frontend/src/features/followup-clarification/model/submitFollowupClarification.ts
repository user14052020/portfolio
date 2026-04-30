import type { ChatResponse } from "@/entities/chat-session/model/types";
import type {
  FrontendProfileContext,
  FrontendProfileUpdate,
} from "@/entities/profile/model/types";
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
  profileContext = null,
  profileRecentUpdate = null,
}: {
  sessionId: string;
  locale: Locale;
  message: string | null;
  assetId?: number | string | null;
  clientMessageId?: string;
  profileContext?: FrontendProfileContext | null;
  profileRecentUpdate?: FrontendProfileUpdate | null;
}): Promise<ChatResponse> {
  return sendFollowupMessage(
    buildFollowupMessagePayload({
      sessionId,
      locale,
      message,
      assetId,
      clientMessageId,
      profileContext,
      profileRecentUpdate,
    })
  );
}
