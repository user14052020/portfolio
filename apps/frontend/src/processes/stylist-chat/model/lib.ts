import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import { adaptFrontendScenarioContext } from "@/entities/stylist-context/model/adapters";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import type { GenerationJobState } from "@/entities/generation-job/model/types";
import type { ChatModeContext, Locale, UploadedAsset } from "@/shared/api/types";

const SESSION_STORAGE_KEY = "portfolio-chat-session";
const CHAT_STATE_STORAGE_KEY_PREFIX = "portfolio-chat-state";
export const GENERATION_STATUS_POLL_INTERVAL_MS = 10000;
export const INITIAL_HISTORY_PAGE_SIZE = 5;

export type PersistedStylistChatUiState = {
  messages: ThreadMessage[];
  uploadedAsset: UploadedAsset | null;
  activeJob: GenerationJobState | null;
};

function createUuidFallback() {
  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const bytes = new Uint8Array(16);
    window.crypto.getRandomValues(bytes);
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = [...bytes].map((value) => value.toString(16).padStart(2, "0"));
    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10, 16).join(""),
    ].join("-");
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function createClientMessageId() {
  if (typeof window !== "undefined" && typeof window.crypto?.randomUUID === "function") {
    return window.crypto.randomUUID();
  }

  return createUuidFallback();
}

export function createSessionId() {
  if (typeof window === "undefined") {
    return "portfolio-preview-session";
  }

  const existing = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }

  const next =
    typeof window.crypto?.randomUUID === "function" ? window.crypto.randomUUID() : createUuidFallback();
  window.localStorage.setItem(SESSION_STORAGE_KEY, next);
  return next;
}

function getChatStateStorageKey(sessionId: string) {
  return `${CHAT_STATE_STORAGE_KEY_PREFIX}:${sessionId}`;
}

export function readPersistedStylistChatUiState(sessionId: string): PersistedStylistChatUiState | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(getChatStateStorageKey(sessionId));
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<PersistedStylistChatUiState>;
    return {
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
      uploadedAsset: parsed.uploadedAsset ?? null,
      activeJob: parsed.activeJob ?? null,
    };
  } catch {
    return null;
  }
}

export function writePersistedStylistChatUiState(
  sessionId: string,
  state: PersistedStylistChatUiState
) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(getChatStateStorageKey(sessionId), JSON.stringify(state));
  } catch {
    // Ignore persistence failures in restrictive browser environments.
  }
}

export function createDefaultScenarioContext(): FrontendScenarioContext {
  const rawContext: ChatModeContext = {
    version: 1,
    active_mode: "general_advice",
    flow_state: "idle",
    clarification_attempts: 0,
    should_auto_generate: false,
    style_history: [],
    conversation_memory: [],
    updated_at: new Date().toISOString(),
  };
  return adaptFrontendScenarioContext(rawContext);
}

export function mergeHistoryIntoCurrent(current: ThreadMessage[], history: ThreadMessage[]) {
  const historyKeys = new Set(
    history.map(
      (message) =>
        `${message.role}::${message.content.trim()}::${message.uploaded_asset?.id ?? "no-asset"}::${message.generation_job?.public_id ?? "no-job"}`
    )
  );
  const pendingMessages = current.filter((message) => {
    if (message.id >= 0) {
      return false;
    }

    const key = `${message.role}::${message.content.trim()}::${message.uploaded_asset?.id ?? "no-asset"}::${message.generation_job?.public_id ?? "no-job"}`;
    return !historyKeys.has(key);
  });

  if (pendingMessages.length === 0) {
    return history;
  }

  return [...history, ...pendingMessages];
}

export function getInitialVisibleMessages(messages: ThreadMessage[]) {
  if (messages.length <= INITIAL_HISTORY_PAGE_SIZE) {
    return messages;
  }

  const persistedMessageIds = new Set(
    messages
      .filter((message) => message.id >= 0)
      .slice(-INITIAL_HISTORY_PAGE_SIZE)
      .map((message) => message.id)
  );

  return messages.filter((message) => message.id < 0 || persistedMessageIds.has(message.id));
}

export function prependHistoryPage(current: ThreadMessage[], olderMessages: ThreadMessage[]) {
  if (olderMessages.length === 0) {
    return current;
  }

  const currentIds = new Set(current.map((message) => message.id));
  const uniqueOlderMessages = olderMessages.filter((message) => !currentIds.has(message.id));
  if (uniqueOlderMessages.length === 0) {
    return current;
  }

  return [...uniqueOlderMessages, ...current];
}

export function mergeQueuedJobState(
  current: GenerationJobState | null,
  next: GenerationJobState
) {
  if (!current || current.status !== "pending" || next.status !== "pending") {
    return next;
  }

  return {
    ...next,
    queue_position: next.queue_position ?? current.queue_position,
    queue_ahead: next.queue_ahead ?? current.queue_ahead,
    queue_total: next.queue_total ?? current.queue_total,
    queue_refresh_available_at:
      next.queue_refresh_available_at ?? current.queue_refresh_available_at,
    queue_refresh_retry_after_seconds:
      next.queue_refresh_retry_after_seconds ?? current.queue_refresh_retry_after_seconds,
  };
}

export function syncGenerationJobInMessages(
  current: ThreadMessage[],
  nextJob: GenerationJobState
) {
  return current.map((message) =>
    message.generation_job?.public_id === nextJob.public_id
      ? {
          ...message,
          generation_job: mergeQueuedJobState(message.generation_job ?? null, nextJob),
        }
      : message
  );
}

export function getLatestGenerationJob(messages: ThreadMessage[]) {
  return (
    [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && message.generation_job)?.generation_job ?? null
  );
}

export function isGenerationJobActive(job: GenerationJobState | null) {
  return job?.status === "pending" || job?.status === "queued" || job?.status === "running";
}

export function isGenerationJobQueued(job: GenerationJobState | null) {
  return job?.status === "pending";
}

export function buildOptimisticDraftMessage(
  input: string,
  uploadedAsset: UploadedAsset | null,
  locale: Locale
) {
  const trimmedInput = input.trim();
  if (trimmedInput) {
    return trimmedInput;
  }

  if (uploadedAsset) {
    return locale === "ru"
      ? `Фото вещи: ${uploadedAsset.original_filename}`
      : `Item photo: ${uploadedAsset.original_filename}`;
  }

  return locale === "ru" ? "Нужно уточнение по образу" : "Need outfit guidance";
}

export function createOptimisticUserMessage({
  sessionId,
  locale,
  input,
  uploadedAsset,
}: {
  sessionId: string;
  locale: Locale;
  input: string;
  uploadedAsset: UploadedAsset | null;
}): ThreadMessage {
  const optimisticId = -Math.floor(Date.now() + Math.random() * 1000);
  const timestamp = new Date().toISOString();
  return {
    id: optimisticId,
    session_id: sessionId,
    role: "user",
    locale,
    content: buildOptimisticDraftMessage(input, uploadedAsset, locale),
    generation_job_id: null,
    generation_job: null,
    uploaded_asset: uploadedAsset,
    payload: {},
    created_at: timestamp,
    updated_at: timestamp,
    isOptimistic: true,
  };
}

export function getComposerMessageSource(
  context: FrontendScenarioContext | null
): "chat_input" | "followup" {
  return context?.commandName ? "followup" : "chat_input";
}

export function getScenarioPlaceholder(
  context: FrontendScenarioContext,
  locale: Locale
) {
  if (context.pendingClarification) {
    return locale === "ru"
      ? "Ответьте на уточнение стилиста..."
      : "Answer the stylist follow-up...";
  }

  if (context.activeMode === "garment_matching") {
    return locale === "ru"
      ? "Опишите вещь или прикрепите фото..."
      : "Describe the garment or attach a photo...";
  }

  if (context.activeMode === "occasion_outfit") {
    return locale === "ru"
      ? "Опишите событие, время и желаемое впечатление..."
      : "Describe the occasion, timing, and desired impression...";
  }

  if (context.activeMode === "style_exploration") {
    return locale === "ru"
      ? "Уточните, что хотите попробовать в новом стиле..."
      : "Add any hint for the next style direction...";
  }

  return locale === "ru"
    ? "Опишите вещь, событие или желаемый стиль..."
    : "Describe the garment, occasion, or style direction...";
}

export function shouldRenderPendingGeneration(response: ChatResponse) {
  return response.decisionType === "text_and_generate" && Boolean(response.jobId || response.generationJob);
}
