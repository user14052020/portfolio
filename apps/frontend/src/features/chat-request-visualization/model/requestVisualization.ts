import type { ChatResponse } from "@/entities/chat-session/model/types";
import { buildProfileRequestEnvelope } from "@/entities/profile/model/profileContext";
import type { FrontendProfileContext } from "@/entities/profile/model/types";
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
    profileContext = null,
  }: {
    sessionId: string;
    locale: Locale;
    visualizationOffer: VisualizationOfferState;
    assetId?: number | string | null;
    clientMessageId?: string;
    profileContext?: FrontendProfileContext | null;
  },
  gateway: VisualizationGateway = visualizationGateway
): Promise<ChatResponse> {
  const visualizationType = visualizationOffer.visualizationType ?? "flat_lay_reference";
  const profileEnvelope = buildProfileRequestEnvelope({ profileContext });
  return gateway.requestVisualization({
    sessionId,
    locale,
    visualizationType,
    assetId: assetId == null ? null : String(assetId),
    profileContext: profileEnvelope.profileContext ?? null,
    metadata: {
      source: "visualization_cta",
      clientMessageId,
      visualizationType,
      ...profileEnvelope.metadata,
    },
  });
}
