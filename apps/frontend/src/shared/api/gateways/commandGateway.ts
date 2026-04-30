import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatCommandPayload } from "@/entities/command/model/types";
import { adaptChatResponse } from "@/entities/chat-session/model/adapters";
import { request } from "@/shared/api/base";
import type { StylistMessageResponse } from "@/shared/api/types";

function toApiAssetId(assetId: string | null) {
  if (!assetId) {
    return undefined;
  }

  const parsed = Number(assetId);
  return Number.isFinite(parsed) ? parsed : undefined;
}

export interface CommandGateway {
  runCommand(payload: ChatCommandPayload): Promise<ChatResponse>;
}

class HttpCommandGateway implements CommandGateway {
  async runCommand(payload: ChatCommandPayload): Promise<ChatResponse> {
    const response = await request<StylistMessageResponse>("/stylist-chat/message", {
      method: "POST",
      body: JSON.stringify({
        session_id: payload.sessionId,
        locale: payload.locale,
        requested_intent: payload.requestedIntent,
        command_name: payload.commandName,
        command_step: payload.commandStep,
        message: payload.message ?? undefined,
        asset_id: toApiAssetId(payload.assetId),
        metadata: payload.metadata ?? {},
        profile_context: payload.profileContext ?? undefined,
      }),
    });

    return adaptChatResponse(response);
  }
}

export const commandGateway: CommandGateway = new HttpCommandGateway();
