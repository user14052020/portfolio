import type { ChatResponse } from "@/entities/chat-session/model/types";
import { adaptChatResponse } from "@/entities/chat-session/model/adapters";
import { request } from "@/shared/api/base";
import type { StylistMessageResponse } from "@/shared/api/types";

function toApiAssetId(assetId: string | null | undefined) {
  if (!assetId) {
    return undefined;
  }

  const parsed = Number(assetId);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export interface VisualizationGateway {
  requestVisualization(payload: {
    sessionId: string;
    locale: string;
    visualizationType: string;
    message?: string | null;
    assetId?: string | null;
    metadata?: Record<string, unknown>;
  }): Promise<ChatResponse>;
}

class HttpVisualizationGateway implements VisualizationGateway {
  async requestVisualization(payload: {
    sessionId: string;
    locale: string;
    visualizationType: string;
    message?: string | null;
    assetId?: string | null;
    metadata?: Record<string, unknown>;
  }): Promise<ChatResponse> {
    const response = await request<StylistMessageResponse>("/stylist-chat/visualize", {
      method: "POST",
      body: JSON.stringify({
        session_id: payload.sessionId,
        locale: payload.locale,
        visualization_type: payload.visualizationType,
        message: payload.message ?? undefined,
        asset_id: toApiAssetId(payload.assetId),
        metadata: payload.metadata ?? {},
      }),
    });
    return adaptChatResponse(response);
  }
}

export const visualizationGateway: VisualizationGateway = new HttpVisualizationGateway();

