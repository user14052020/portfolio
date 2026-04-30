import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatCommandPayload, CommandName } from "@/entities/command/model/types";
import { buildProfileRequestEnvelope } from "@/entities/profile/model/profileContext";
import type { FrontendProfileContext } from "@/entities/profile/model/types";
import { commandGateway, type CommandGateway } from "@/shared/api/gateways/commandGateway";
import type { Locale } from "@/shared/api/types";

export interface QuickActionDefinition {
  id: CommandName;
  kind: "style";
  label: string;
  requestedIntent: "style_exploration";
  commandName: "style_exploration";
  commandStep: "start";
}

export function getQuickActionDefinitions(locale: Locale): QuickActionDefinition[] {
  if (locale === "ru") {
    return [
      {
        id: "style_exploration",
        kind: "style",
        label: "Попробовать другой стиль",
        requestedIntent: "style_exploration",
        commandName: "style_exploration",
        commandStep: "start",
      },
    ];
  }

  return [
    {
      id: "style_exploration",
      kind: "style",
      label: "Try another style",
      requestedIntent: "style_exploration",
      commandName: "style_exploration",
      commandStep: "start",
    },
  ];
}

export function buildQuickActionCommandPayload({
  sessionId,
  locale,
  action,
  clientMessageId,
  profileContext = null,
}: {
  sessionId: string;
  locale: Locale;
  action: QuickActionDefinition;
  assetId?: number | string | null;
  clientMessageId?: string;
  profileContext?: FrontendProfileContext | null;
}): ChatCommandPayload {
  const profileEnvelope = buildProfileRequestEnvelope({ profileContext });

  return {
    sessionId,
    locale,
    requestedIntent: action.requestedIntent,
    commandName: action.commandName,
    commandStep: action.commandStep,
    message: null,
    assetId: null,
    profileContext: profileEnvelope.profileContext ?? null,
    metadata: {
      source: "quick_action",
      clientMessageId,
      uiLocale: locale,
      ...profileEnvelope.metadata,
    },
  };
}

export async function runQuickActionCommand(
  payload: ChatCommandPayload,
  gateway: CommandGateway = commandGateway
): Promise<ChatResponse> {
  return gateway.runCommand(payload);
}
