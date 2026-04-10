import type { ChatMode, Locale } from "@/shared/api/types";

export type CommandName = Exclude<ChatMode, "general_advice">;
export type CommandStep = "start" | "followup" | "resume";
export type CommandSource = "quick_action" | "chat_input" | "retry" | "system_resume";
export type MessageSource = "chat_input" | "followup" | "system_retry";

export interface CommandMetadata {
  source: CommandSource;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
  uiLocale?: Locale;
}

export interface MessageMetadata {
  source: MessageSource;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
}

export interface ChatCommandPayload {
  sessionId: string;
  locale: Locale;
  requestedIntent: ChatMode;
  commandName: CommandName;
  commandStep: CommandStep;
  message: string | null;
  assetId: string | null;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
  metadata?: CommandMetadata;
}

export interface ChatMessagePayload {
  sessionId: string;
  locale: Locale;
  message: string | null;
  assetId?: string | null;
  requestedIntent?: ChatMode | null;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
  metadata?: MessageMetadata;
}
