import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatMessagePayload } from "@/entities/command/model/types";
import { chatGateway, type ChatGateway } from "@/shared/api/gateways/chatGateway";
import type { Locale } from "@/shared/api/types";

export function buildFreeformMessagePayload({
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
}): ChatMessagePayload {
  return {
    sessionId,
    locale,
    message,
    assetId: assetId == null ? null : String(assetId),
    metadata: {
      source: "chat_input",
      clientMessageId,
    },
  };
}

export function buildFollowupMessagePayload({
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
}): ChatMessagePayload {
  return {
    sessionId,
    locale,
    message,
    assetId: assetId == null ? null : String(assetId),
    metadata: {
      source: "followup",
      clientMessageId,
    },
  };
}

export async function sendFreeformMessage(
  payload: ChatMessagePayload,
  gateway: ChatGateway = chatGateway
): Promise<ChatResponse> {
  return gateway.sendMessage(payload);
}

export async function sendFollowupMessage(
  payload: ChatMessagePayload,
  gateway: ChatGateway = chatGateway
): Promise<ChatResponse> {
  return gateway.sendMessage(payload);
}
