import type { ChatMessage } from "@/shared/api/types";

export interface ThreadMessage extends ChatMessage {
  isOptimistic?: boolean;
}
