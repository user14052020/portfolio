import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatMessagePayload } from "@/entities/command/model/types";
import { adaptChatResponse } from "@/entities/chat-session/model/adapters";
import { request } from "@/shared/api/base";
import type { ChatHistoryPage, StylistMessageResponse } from "@/shared/api/types";

function toApiAssetId(assetId: string | null | undefined) {
  if (!assetId) {
    return undefined;
  }

  const parsed = Number(assetId);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export interface ChatGateway {
  sendMessage(payload: ChatMessagePayload): Promise<ChatResponse>;
  getHistoryPage(
    sessionId: string,
    params?: {
      limit?: number;
      beforeMessageId?: number | null;
    }
  ): Promise<ChatHistoryPage>;
}

class HttpChatGateway implements ChatGateway {
  async sendMessage(payload: ChatMessagePayload): Promise<ChatResponse> {
    const response = await request<StylistMessageResponse>("/stylist-chat/message", {
      method: "POST",
      body: JSON.stringify({
        session_id: payload.sessionId,
        locale: payload.locale,
        message: payload.message ?? undefined,
        asset_id: toApiAssetId(payload.assetId),
        requested_intent: payload.requestedIntent ?? undefined,
        metadata: payload.metadata ?? {},
      }),
    });

    return adaptChatResponse(response);
  }

  async getHistoryPage(
    sessionId: string,
    params?: {
      limit?: number;
      beforeMessageId?: number | null;
    }
  ): Promise<ChatHistoryPage> {
    return request<ChatHistoryPage>(`/stylist-chat/history/${sessionId}`, {
      query: {
        limit: params?.limit,
        before_message_id: params?.beforeMessageId ?? undefined,
      },
    });
  }
}

export const chatGateway: ChatGateway = new HttpChatGateway();
