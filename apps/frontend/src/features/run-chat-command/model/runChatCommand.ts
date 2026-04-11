import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ChatCommandPayload, CommandName } from "@/entities/command/model/types";
import { commandGateway, type CommandGateway } from "@/shared/api/gateways/commandGateway";
import type { Locale } from "@/shared/api/types";

export interface QuickActionDefinition {
  id: CommandName;
  kind: "pair" | "style" | "occasion";
  label: string;
  requestedIntent: CommandName;
  commandName: CommandName;
  commandStep: "start";
}

export function getQuickActionDefinitions(locale: Locale): QuickActionDefinition[] {
  if (locale === "ru") {
    return [
      {
        id: "garment_matching",
        kind: "pair",
        label: "Подобрать к вещи",
        requestedIntent: "garment_matching",
        commandName: "garment_matching",
        commandStep: "start",
      },
      {
        id: "style_exploration",
        kind: "style",
        label: "Попробовать другой стиль",
        requestedIntent: "style_exploration",
        commandName: "style_exploration",
        commandStep: "start",
      },
      {
        id: "occasion_outfit",
        kind: "occasion",
        label: "Что надеть на событие",
        requestedIntent: "occasion_outfit",
        commandName: "occasion_outfit",
        commandStep: "start",
      },
    ];
  }

  return [
    {
      id: "garment_matching",
      kind: "pair",
      label: "Style a garment",
      requestedIntent: "garment_matching",
      commandName: "garment_matching",
      commandStep: "start",
    },
    {
      id: "style_exploration",
      kind: "style",
      label: "Try another style",
      requestedIntent: "style_exploration",
      commandName: "style_exploration",
      commandStep: "start",
    },
    {
      id: "occasion_outfit",
      kind: "occasion",
      label: "What should I wear?",
      requestedIntent: "occasion_outfit",
      commandName: "occasion_outfit",
      commandStep: "start",
    },
  ];
}

export function buildQuickActionCommandPayload({
  sessionId,
  locale,
  action,
  assetId = null,
  clientMessageId,
}: {
  sessionId: string;
  locale: Locale;
  action: QuickActionDefinition;
  assetId?: number | string | null;
  clientMessageId?: string;
}): ChatCommandPayload {
  const shouldSuppressAsset =
    action.id === "occasion_outfit" || action.id === "style_exploration" || assetId == null;
  return {
    sessionId,
    locale,
    requestedIntent: action.requestedIntent,
    commandName: action.commandName,
    commandStep: action.commandStep,
    message: null,
    assetId: shouldSuppressAsset ? null : String(assetId),
    metadata: {
      source: "quick_action",
      clientMessageId,
      uiLocale: locale,
    },
  };
}

export async function runQuickActionCommand(
  payload: ChatCommandPayload,
  gateway: CommandGateway = commandGateway
): Promise<ChatResponse> {
  return gateway.runCommand(payload);
}
