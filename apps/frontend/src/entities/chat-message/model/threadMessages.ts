import type { ThreadMessage } from "@/entities/chat-message/model/types";

export function appendMessageDedupingAdjacentClarification(
  current: ThreadMessage[],
  nextMessage: ThreadMessage,
) {
  const previous = current[current.length - 1];
  if (previous && isDuplicateAssistantClarificationMessage(previous, nextMessage)) {
    return current;
  }
  return [...current, nextMessage];
}

export function dedupeAdjacentAssistantClarificationMessages(messages: ThreadMessage[]) {
  return messages.reduce<ThreadMessage[]>((deduped, message) => {
    const previous = deduped[deduped.length - 1];
    if (previous && isDuplicateAssistantClarificationMessage(previous, message)) {
      return deduped;
    }
    deduped.push(message);
    return deduped;
  }, []);
}

function isDuplicateAssistantClarificationMessage(left: ThreadMessage, right: ThreadMessage) {
  if (!isAssistantClarificationMessage(left) || !isAssistantClarificationMessage(right)) {
    return false;
  }

  return (
    normalizeMessageContent(left.content) === normalizeMessageContent(right.content) &&
    optionalPayloadString(left, "clarification_kind") === optionalPayloadString(right, "clarification_kind") &&
    optionalPayloadString(left, "active_mode") === optionalPayloadString(right, "active_mode")
  );
}

function isAssistantClarificationMessage(message: ThreadMessage) {
  return (
    message.role === "assistant" &&
    (
      message.payload?.decision_type === "clarification_required" ||
      message.payload?.kind === "clarification_required"
    )
  );
}

function normalizeMessageContent(content: string) {
  return content.trim().replace(/\s+/g, " ");
}

function optionalPayloadString(message: ThreadMessage, key: string) {
  const value = message.payload?.[key];
  return typeof value === "string" ? value : null;
}
