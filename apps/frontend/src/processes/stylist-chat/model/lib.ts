import type { ChatResponse } from "@/entities/chat-session/model/types";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import { normalizeProfileContext } from "@/entities/profile/model/profileContext";
import type { FrontendProfileContext } from "@/entities/profile/model/types";
import { adaptFrontendScenarioContext } from "@/entities/stylist-context/model/adapters";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import type { GenerationJobState } from "@/entities/generation-job/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import type { ChatModeContext, Locale, UploadedAsset } from "@/shared/api/types";

const SESSION_STORAGE_KEY = "portfolio-chat-session";
const CHAT_STATE_STORAGE_KEY_PREFIX = "portfolio-chat-state";
export const GENERATION_STATUS_POLL_INTERVAL_MS = 10000;
export const INITIAL_HISTORY_PAGE_SIZE = 5;
export const LOCAL_CHAT_RETENTION_DAYS = 10;
const LOCAL_CHAT_RETENTION_MS = LOCAL_CHAT_RETENTION_DAYS * 24 * 60 * 60 * 1000;
const PENDING_OPTIMISTIC_MESSAGE_TTL_MS = 2 * 60 * 1000;

export type PersistedStylistChatUiState = {
  messages: ThreadMessage[];
  uploadedAsset: UploadedAsset | null;
  activeJob: GenerationJobState | null;
  visualizationOffer: VisualizationOfferState;
  lastUserActionType: string | null;
  lastVisualCtaShown: string | null;
  lastVisualCtaConfirmed: string | null;
  profileContext: FrontendProfileContext;
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
    const prunedState = prunePersistedStylistChatUiState({
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
      uploadedAsset: parsed.uploadedAsset ?? null,
      activeJob: parsed.activeJob ?? null,
      visualizationOffer: parsed.visualizationOffer ?? {
        canOfferVisualization: false,
        ctaText: null,
        visualizationType: null,
      },
      lastUserActionType: typeof parsed.lastUserActionType === "string" ? parsed.lastUserActionType : null,
      lastVisualCtaShown: typeof parsed.lastVisualCtaShown === "string" ? parsed.lastVisualCtaShown : null,
      lastVisualCtaConfirmed:
        typeof parsed.lastVisualCtaConfirmed === "string" ? parsed.lastVisualCtaConfirmed : null,
      profileContext: normalizeProfileContext(
        parsed.profileContext
          ?? (parsed as Partial<{ presentationProfile: unknown }>).presentationProfile
          ?? {},
      ),
    });
    try {
      window.localStorage.setItem(getChatStateStorageKey(sessionId), JSON.stringify(prunedState));
    } catch {
      // Reading should still succeed if browser storage refuses the cleanup write.
    }
    return prunedState;
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
    window.localStorage.setItem(getChatStateStorageKey(sessionId), JSON.stringify(prunePersistedStylistChatUiState(state)));
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
    visualization_offer: null,
    updated_at: new Date().toISOString(),
  };
  return adaptFrontendScenarioContext(rawContext);
}

export function mergeHistoryIntoCurrent(current: ThreadMessage[], history: ThreadMessage[]) {
  const now = Date.now();
  const retainedHistory = pruneMessagesByRetention(history, now);
  const historyKeys = new Set(
    retainedHistory.map(
      (message) =>
        `${message.role}::${message.content.trim()}::${message.uploaded_asset?.id ?? "no-asset"}::${message.generation_job?.public_id ?? "no-job"}`
    )
  );
  const pendingMessages = pruneMessagesByRetention(current, now).filter((message) => {
    if (!isFreshOptimisticMessage(message, now)) {
      return false;
    }

    const key = `${message.role}::${message.content.trim()}::${message.uploaded_asset?.id ?? "no-asset"}::${message.generation_job?.public_id ?? "no-job"}`;
    return !historyKeys.has(key);
  });

  if (pendingMessages.length === 0) {
    return retainedHistory;
  }

  return sortThreadMessagesChronologically([...retainedHistory, ...pendingMessages]);
}

export function getInitialVisibleMessages(messages: ThreadMessage[]) {
  const now = Date.now();
  const retainedMessages = pruneMessagesByRetention(messages, now);
  if (retainedMessages.length <= INITIAL_HISTORY_PAGE_SIZE) {
    return retainedMessages.filter((message) => message.id >= 0 || isFreshOptimisticMessage(message, now));
  }

  const persistedMessageIds = new Set(
    retainedMessages
      .filter((message) => message.id >= 0)
      .slice(-INITIAL_HISTORY_PAGE_SIZE)
      .map((message) => message.id)
  );

  return retainedMessages.filter(
    (message) => isFreshOptimisticMessage(message, now) || persistedMessageIds.has(message.id)
  );
}

export function prunePersistedStylistChatUiState(
  state: PersistedStylistChatUiState,
  now: number = Date.now()
): PersistedStylistChatUiState {
  const messages = pruneMessagesByRetention(state.messages, now);
  const activeJob =
    state.activeJob && isTimestampWithinLocalRetention(state.activeJob.created_at, now)
      ? state.activeJob
      : null;
  const uploadedAsset =
    state.uploadedAsset && isTimestampWithinLocalRetention(state.uploadedAsset.created_at, now)
      ? state.uploadedAsset
      : null;

  return {
    ...state,
    messages,
    activeJob,
    uploadedAsset,
    profileContext: normalizeProfileContext(state.profileContext),
  };
}

function pruneMessagesByRetention(messages: ThreadMessage[], now: number) {
  return messages
    .filter((message) => isTimestampWithinLocalRetention(message.created_at, now))
    .map((message) => pruneMessageReferencesByRetention(message, now));
}

function pruneMessageReferencesByRetention(message: ThreadMessage, now: number): ThreadMessage {
  const generationJob =
    message.generation_job && isTimestampWithinLocalRetention(message.generation_job.created_at, now)
      ? message.generation_job
      : null;
  const uploadedAsset =
    message.uploaded_asset && isTimestampWithinLocalRetention(message.uploaded_asset.created_at, now)
      ? message.uploaded_asset
      : null;

  if (generationJob === message.generation_job && uploadedAsset === message.uploaded_asset) {
    return message;
  }

  return {
    ...message,
    generation_job_id: generationJob ? message.generation_job_id : null,
    generation_job: generationJob,
    uploaded_asset: uploadedAsset,
  };
}

function isTimestampWithinLocalRetention(timestamp: string | undefined, now: number) {
  if (!timestamp) {
    return false;
  }

  const createdAtMs = Date.parse(timestamp);
  if (!Number.isFinite(createdAtMs)) {
    return false;
  }

  return now - createdAtMs <= LOCAL_CHAT_RETENTION_MS;
}

function isFreshOptimisticMessage(message: ThreadMessage, now: number) {
  if (message.id >= 0 || message.isOptimistic !== true) {
    return false;
  }

  const createdAtMs = Date.parse(message.created_at);
  if (!Number.isFinite(createdAtMs)) {
    return false;
  }

  return now - createdAtMs <= PENDING_OPTIMISTIC_MESSAGE_TTL_MS;
}

function sortThreadMessagesChronologically(messages: ThreadMessage[]) {
  return [...messages].sort((left, right) => {
    const leftTime = Date.parse(left.created_at);
    const rightTime = Date.parse(right.created_at);
    if (!Number.isFinite(leftTime) || !Number.isFinite(rightTime) || leftTime === rightTime) {
      return 0;
    }
    return leftTime - rightTime;
  });
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

export function getLatestVisualizationOffer(messages: ThreadMessage[]): VisualizationOfferState {
  const assistantMessage = [...messages].reverse().find((message) => message.role === "assistant");
  const rawPayload = assistantMessage?.payload ?? {};
  const canOfferVisualization = rawPayload?.can_offer_visualization === true;
  return {
    canOfferVisualization,
    ctaText: canOfferVisualization && typeof rawPayload?.cta_text === "string" ? rawPayload.cta_text : null,
    visualizationType:
      canOfferVisualization && typeof rawPayload?.visualization_type === "string"
        ? rawPayload.visualization_type
        : null,
  };
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

  return locale === "ru" ? "Нужна рекомендация по образу" : "Need outfit guidance";
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
  return context?.pendingClarification ? "followup" : "chat_input";
}

export function getScenarioPlaceholder(
  context: FrontendScenarioContext,
  locale: Locale
) {
  if (locale === "ru") {
    return getRussianScenarioPlaceholder(context);
  }

  if (context.pendingClarification) {
    return locale === "ru"
      ? "Ответьте на уточнение стилиста..."
      : "Answer the stylist follow-up...";
  }

  if (context.activeMode === "occasion_outfit") {
    return locale === "ru"
      ? "Например: вечерняя выставка современного искусства осенью, хочу выглядеть интеллектуально и немного смело"
      : "For example: an evening contemporary art exhibition in autumn, I want to look thoughtful and a little bold";
  }

  if (context.activeMode === "garment_matching") {
    return locale === "ru"
      ? "Например: тёмно-синяя джинсовая рубашка oversize"
      : "For example: a dark indigo oversized denim shirt";
  }

  if (context.activeMode === "style_exploration") {
    return locale === "ru"
      ? "Например: попробуем что-то мягче и теплее, без повторения прошлой палитры"
      : "For example: something softer and warmer, with a different palette and silhouette";
  }

  return locale === "ru"
    ? "Опишите вещь, событие или желаемый стиль..."
    : "Describe the garment, occasion, or style direction...";
}

export function shouldRenderPendingGeneration(response: ChatResponse) {
  return response.decisionType === "text_and_generate" && Boolean(response.jobId || response.generationJob);
}

function getRussianScenarioPlaceholder(context: FrontendScenarioContext) {
  if (context.pendingClarification) {
    return "Ответьте на уточнение стилиста...";
  }

  if (context.activeMode === "occasion_outfit") {
    return "Например: вечерняя выставка современного искусства осенью, хочу выглядеть интеллектуально и немного смело";
  }

  if (context.activeMode === "garment_matching") {
    return "Например: тёмно-синяя джинсовая рубашка oversize";
  }

  if (context.activeMode === "style_exploration") {
    return "Например: попробуем что-то мягче и теплее, без повторения прошлой палитры";
  }

  return "Опишите вещь, событие или желаемый стиль...";
}
