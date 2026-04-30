import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatMessagePayload } from "@/entities/command/model/types";
import { buildProfileRequestEnvelope } from "@/entities/profile/model/profileContext";
import type {
  FrontendProfileContext,
  FrontendProfileUpdate,
} from "@/entities/profile/model/types";
import { chatGateway, type ChatGateway } from "@/shared/api/gateways/chatGateway";
import type { Locale } from "@/shared/api/types";

export function buildFreeformMessagePayload({
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
}): ChatMessagePayload {
  const profileEnvelope = buildProfileRequestEnvelope({
    profileContext,
    recentUpdate: profileRecentUpdate,
  });

  return {
    sessionId,
    locale,
    message,
    assetId: assetId == null ? null : String(assetId),
    profileContext: profileEnvelope.profileContext ?? null,
    metadata: {
      source: "chat_input",
      clientMessageId,
      ...profileEnvelope.metadata,
    },
  };
}

export function buildFollowupMessagePayload({
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
}): ChatMessagePayload {
  const profileEnvelope = buildProfileRequestEnvelope({
    profileContext,
    recentUpdate: profileRecentUpdate,
  });

  return {
    sessionId,
    locale,
    message,
    assetId: assetId == null ? null : String(assetId),
    profileContext: profileEnvelope.profileContext ?? null,
    metadata: {
      source: "followup",
      clientMessageId,
      ...profileEnvelope.metadata,
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
