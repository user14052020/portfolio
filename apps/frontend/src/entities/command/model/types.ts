import type { FrontendProfileContext } from "@/entities/profile/model/types";
import type { ChatMode, Locale } from "@/shared/api/types";

export type CommandName = Exclude<ChatMode, "general_advice">;
export type CommandStep = "start" | "followup" | "resume";
export type CommandSource =
  | "quick_action"
  | "chat_input"
  | "retry"
  | "system_resume"
  | "visualization_cta";
export type MessageSource = "chat_input" | "followup" | "system_retry" | "visualization_cta";

export interface CommandMetadata {
  source: CommandSource;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
  uiLocale?: Locale;
  session_profile_context?: FrontendProfileContext;
  profile_recent_updates?: FrontendProfileContext;
  [key: string]: unknown;
}

export interface MessageMetadata {
  source: MessageSource;
  clientMessageId?: string;
  commandId?: string;
  correlationId?: string;
  session_profile_context?: FrontendProfileContext;
  profile_recent_updates?: FrontendProfileContext;
  [key: string]: unknown;
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
  profileContext?: FrontendProfileContext | null;
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
  profileContext?: FrontendProfileContext | null;
}
