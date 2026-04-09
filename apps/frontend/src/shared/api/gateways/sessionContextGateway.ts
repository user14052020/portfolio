import { adaptFrontendScenarioContext } from "@/entities/stylist-context/model/adapters";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import { request } from "@/shared/api/base";
import type { ChatModeContext } from "@/shared/api/types";

export interface SessionContextGateway {
  getContext(sessionId: string): Promise<FrontendScenarioContext>;
}

class HttpSessionContextGateway implements SessionContextGateway {
  async getContext(sessionId: string): Promise<FrontendScenarioContext> {
    const response = await request<ChatModeContext>(`/stylist-chat/context/${sessionId}`);
    return adaptFrontendScenarioContext(response);
  }
}

export const sessionContextGateway: SessionContextGateway = new HttpSessionContextGateway();
