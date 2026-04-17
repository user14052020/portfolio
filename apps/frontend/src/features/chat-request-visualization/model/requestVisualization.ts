import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import { visualizationGateway, type VisualizationGateway } from "@/shared/api/gateways/visualizationGateway";
import type { Locale } from "@/shared/api/types";

export async function requestVisualization(
  {
    sessionId,
    locale,
    visualizationOffer,
    assetId = null,
    clientMessageId,
  }: {
    sessionId: string;
    locale: Locale;
    visualizationOffer: VisualizationOfferState;
    assetId?: number | string | null;
    clientMessageId?: string;
  },
  gateway: VisualizationGateway = visualizationGateway
): Promise<ChatResponse> {
  const visualizationType = visualizationOffer.visualizationType ?? "flat_lay_reference";
  return gateway.requestVisualization({
    sessionId,
    locale,
    visualizationType,
    assetId: assetId == null ? null : String(assetId),
    metadata: {
      source: "visualization_cta",
      clientMessageId,
      visualizationType,
    },
  });
}
