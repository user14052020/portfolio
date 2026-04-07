"use client";

import { useEffect, useRef, useState } from "react";

import {
  getChatHistoryPage,
  getGenerationJob,
  refreshGenerationJobQueue,
  sendStylistMessage,
  uploadAsset
} from "@/shared/api/client";
import type { ChatMessage, GenerationJob, Locale, UploadedAsset } from "@/shared/api/types";

const SESSION_STORAGE_KEY = "portfolio-chat-session";
const CHAT_STATE_STORAGE_KEY_PREFIX = "portfolio-chat-state";
const PROFILE_STORAGE_KEY = "portfolio-chat-profile";
const GENERATION_STATUS_POLL_INTERVAL_MS = 10000;
const INITIAL_HISTORY_PAGE_SIZE = 5;
const MESSAGE_COOLDOWN_SECONDS = 60;
const GENERATION_HINTS = [
  "generate",
  "render",
  "visualize",
  "visualise",
  "lookbook",
  "flat lay",
  "flat-lay",
  "сгенер",
  "визуал",
  "покажи",
  "пример образа"
];

type PersistedChatState = {
  messages: ChatMessage[];
  uploadedAsset: UploadedAsset | null;
  activeJob: GenerationJob | null;
};

type BackendState = "connecting" | "connected" | "error";
type ChatAvailability = "online" | "offline";
type RequestedIntent = "garment_matching" | "style_exploration" | "occasion_outfit";

type StoredProfile = {
  gender: "male" | "female" | "";
  heightCm: string;
  weightKg: string;
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
      hex.slice(10, 16).join("")
    ].join("-");
  }

  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createSessionId() {
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

function readPersistedChatState(sessionId: string): PersistedChatState | null {
  if (typeof window === "undefined") {
    return null;
  }

  try {
    const raw = window.localStorage.getItem(getChatStateStorageKey(sessionId));
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<PersistedChatState>;
    return {
      messages: Array.isArray(parsed.messages) ? parsed.messages : [],
      uploadedAsset: parsed.uploadedAsset ?? null,
      activeJob: parsed.activeJob ?? null,
    };
  } catch {
    return null;
  }
}

function writePersistedChatState(sessionId: string, state: PersistedChatState) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(getChatStateStorageKey(sessionId), JSON.stringify(state));
  } catch {
    // Ignore storage failures so the chat remains usable in restrictive environments.
  }
}

function readStoredProfile(): StoredProfile {
  if (typeof window === "undefined") {
    return { gender: "", heightCm: "", weightKg: "" };
  }

  try {
    const raw = window.localStorage.getItem(PROFILE_STORAGE_KEY);
    if (!raw) {
      return { gender: "", heightCm: "", weightKg: "" };
    }

    const parsed = JSON.parse(raw) as Partial<StoredProfile>;
    return {
      gender: parsed.gender === "male" || parsed.gender === "female" ? parsed.gender : "",
      heightCm: typeof parsed.heightCm === "string" ? parsed.heightCm : "",
      weightKg: typeof parsed.weightKg === "string" ? parsed.weightKg : "",
    };
  } catch {
    return { gender: "", heightCm: "", weightKg: "" };
  }
}

function writeStoredProfile(profile: StoredProfile) {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
  } catch {
    // Ignore storage failures so the chat remains usable in restrictive environments.
  }
}

function normalizeProfileGender(value: unknown): StoredProfile["gender"] {
  if (typeof value !== "string") {
    return "";
  }

  const lowered = value.trim().toLowerCase();
  if (["male", "man", "m", "м", "муж", "мужчина", "парень"].includes(lowered)) {
    return "male";
  }
  if (["female", "woman", "f", "ж", "жен", "женщина", "девушка"].includes(lowered)) {
    return "female";
  }
  return "";
}

function normalizeProfileNumber(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(Math.trunc(value));
  }
  if (typeof value === "string") {
    return value.replace(/[^\d]/g, "").slice(0, 3);
  }
  return "";
}

function extractGenderFromText(text: string): StoredProfile["gender"] {
  const lowered = text.toLowerCase();
  if (/\b(мужчина|парень|male|man|guy)\b/.test(lowered)) {
    return "male";
  }
  if (/\b(женщина|девушка|female|woman|girl)\b/.test(lowered)) {
    return "female";
  }
  return "";
}

function extractHeightCmFromText(text: string) {
  const lowered = text.toLowerCase();
  const namedMatch = lowered.match(/(?:(?:рост)|height)\s*[:\-]?\s*(\d{2,3})/);
  if (namedMatch?.[1]) {
    return normalizeProfileNumber(namedMatch[1]);
  }

  const cmMatch = lowered.match(/\b(\d{3})\s*(?:см|cm)\b/);
  if (cmMatch?.[1]) {
    return normalizeProfileNumber(cmMatch[1]);
  }

  const meterMatch = lowered.match(/\b(1[.,]\d{2})\s*(?:м|m)\b/);
  if (meterMatch?.[1]) {
    const metersValue = Number.parseFloat(meterMatch[1].replace(",", "."));
    return Number.isFinite(metersValue) ? String(Math.round(metersValue * 100)) : "";
  }

  return "";
}

function extractWeightKgFromText(text: string) {
  const lowered = text.toLowerCase();
  const namedMatch = lowered.match(/(?:(?:вес)|weight)\s*[:\-]?\s*(\d{2,3})/);
  if (namedMatch?.[1]) {
    return normalizeProfileNumber(namedMatch[1]);
  }

  const kgMatch = lowered.match(/\b(\d{2,3})\s*(?:кг|kg)\b/);
  if (kgMatch?.[1]) {
    return normalizeProfileNumber(kgMatch[1]);
  }

  return "";
}

function mergeStoredProfile(current: StoredProfile, next: Partial<StoredProfile>): StoredProfile {
  return {
    gender: next.gender || current.gender,
    heightCm: next.heightCm || current.heightCm,
    weightKg: next.weightKg || current.weightKg,
  };
}

function extractProfileFromMessages(messages: ChatMessage[], fallbackProfile: StoredProfile): StoredProfile {
  let profile = fallbackProfile;

  for (const message of messages) {
    const payload = message.payload && typeof message.payload === "object" ? message.payload : {};
    const profileContext =
      payload.profile_context && typeof payload.profile_context === "object"
        ? (payload.profile_context as Record<string, unknown>)
        : {};

    profile = mergeStoredProfile(profile, {
      gender:
        normalizeProfileGender(payload.profile_gender) ||
        normalizeProfileGender(profileContext.gender) ||
        (message.role === "user" ? extractGenderFromText(message.content) : ""),
      heightCm:
        normalizeProfileNumber(payload.body_height_cm) ||
        normalizeProfileNumber(profileContext.height_cm) ||
        (message.role === "user" ? extractHeightCmFromText(message.content) : ""),
      weightKg:
        normalizeProfileNumber(payload.body_weight_kg) ||
        normalizeProfileNumber(profileContext.weight_kg) ||
        (message.role === "user" ? extractWeightKgFromText(message.content) : ""),
    });
  }

  return profile;
}

function parseOptionalNumber(value: string) {
  if (!value.trim()) {
    return undefined;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function getChatOfflineMessage(locale: Locale) {
  return locale === "ru"
    ? "Чат временно офлайн: языковая модель недоступна. Как только LLM снова поднимется, сообщения и команды снова станут доступны."
    : "The chat is temporarily offline because the language model is unavailable. Messages and commands will become available again once it is back.";
}

function isServiceUnavailableError(error: unknown): error is Error & { status?: number } {
  return false;
}

function shouldMarkChatOffline(error: unknown) {
  if (isServiceUnavailableError(error)) {
    return true;
  }

  if (!(error instanceof Error)) {
    return false;
  }

  const status = typeof (error as { status?: number }).status === "number" ? (error as { status?: number }).status : undefined;
  if (status === 502 || status === 504) {
    return true;
  }

  return /failed to fetch|networkerror|load failed|fetch failed/i.test(error.message);
}

void getChatOfflineMessage;
void shouldMarkChatOffline;

function mergeHistoryIntoCurrent(current: ChatMessage[], history: ChatMessage[]) {
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

function getInitialVisibleMessages(messages: ChatMessage[]) {
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

function prependHistoryPage(current: ChatMessage[], olderMessages: ChatMessage[]) {
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

function mergeQueuedJobState(current: GenerationJob | null, next: GenerationJob) {
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

function syncGenerationJobInMessages(current: ChatMessage[], nextJob: GenerationJob) {
  return current.map((message) =>
    message.generation_job?.public_id === nextJob.public_id
      ? {
          ...message,
          generation_job: mergeQueuedJobState(message.generation_job, nextJob),
        }
      : message
  );
}

function getLastAssistantMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "assistant");
}

function getLatestGenerationJob(messages: ChatMessage[]) {
  return (
    [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && message.generation_job)?.generation_job ?? null
  );
}

function isGenerationJobActive(job: GenerationJob | null) {
  return job?.status === "pending" || job?.status === "queued" || job?.status === "running";
}

function isGenerationJobQueued(job: GenerationJob | null) {
  return job?.status === "pending";
}

function shouldAutoGenerateMessage({
  input,
  uploadedAsset,
  explicitAutoGenerate
}: {
  input: string;
  uploadedAsset: UploadedAsset | null;
  explicitAutoGenerate?: boolean;
}) {
  if (typeof explicitAutoGenerate === "boolean") {
    return explicitAutoGenerate;
  }

  if (uploadedAsset) {
    return true;
  }

  const lowered = input.trim().toLowerCase();
  return GENERATION_HINTS.some((hint) => lowered.includes(hint));
}

function getLastUserMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "user");
}

function getLastAssistantMessageForCooldown(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "assistant");
}

function getMessageCooldownEndsAt(messages: ChatMessage[]) {
  const lastAssistantMessage = getLastAssistantMessageForCooldown(messages);
  if (!lastAssistantMessage?.created_at) {
    return null;
  }

  const lastSentAt = Date.parse(lastAssistantMessage.created_at);
  if (Number.isNaN(lastSentAt)) {
    return null;
  }

  return lastSentAt + MESSAGE_COOLDOWN_SECONDS * 1000;
}

function getRemainingSeconds(endsAt: number | null, now: number) {
  if (!endsAt) {
    return 0;
  }

  return Math.max(0, Math.ceil((endsAt - now) / 1000));
}

function getErrorPayloadDetail(error: unknown) {
  if (!(error instanceof Error)) {
    return null;
  }

  const payload = (error as Error & { payload?: unknown }).payload;
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return null;
  }

  const detail = (payload as { detail?: unknown }).detail;
  return detail && typeof detail === "object" ? (detail as Record<string, unknown>) : null;
}

function buildDraftMessage(input: string, uploadedAsset: UploadedAsset | null, locale: Locale) {
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

export function useStylistChat(locale: Locale) {
  const [bootstrap] = useState(() => {
    const nextSessionId = createSessionId();
    const persistedState = readPersistedChatState(nextSessionId);
    return {
      sessionId: nextSessionId,
      persistedState: persistedState
        ? {
            ...persistedState,
            messages: getInitialVisibleMessages(persistedState.messages),
          }
        : null
    };
  });
  const sessionId = bootstrap.sessionId;
  const persistedState = bootstrap.persistedState;

  const [messages, setMessages] = useState<ChatMessage[]>(() => persistedState?.messages ?? []);
  const [input, setInput] = useState("");
  const [uploadedAsset, setUploadedAsset] = useState<UploadedAsset | null>(
    () => persistedState?.uploadedAsset ?? null
  );
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(
    () => persistedState?.activeJob ?? getLatestGenerationJob(persistedState?.messages ?? [])
  );
  const [isHistoryLoading, setIsHistoryLoading] = useState(messages.length === 0);
  const [isLoadingOlderHistory, setIsLoadingOlderHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [nextHistoryCursor, setNextHistoryCursor] = useState<number | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerationPreparing, setIsGenerationPreparing] = useState(false);
  const [isRefreshingQueue, setIsRefreshingQueue] = useState(false);
  const [backendState, setBackendState] = useState<BackendState>("connected");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [storedProfile, setStoredProfile] = useState<StoredProfile>(() => readStoredProfile());
  const [clockTick, setClockTick] = useState(() => Date.now());
  const messagesRef = useRef(messages);
  const chatAvailability: ChatAvailability = "online";
  const messageCooldownEndsAt = getMessageCooldownEndsAt(messages);
  const messageCooldownRemainingSeconds = getRemainingSeconds(messageCooldownEndsAt, clockTick);
  const queueRefreshAvailableAt = activeJob?.queue_refresh_available_at
    ? Date.parse(activeJob.queue_refresh_available_at)
    : null;
  const queueRefreshRemainingSeconds = getRemainingSeconds(queueRefreshAvailableAt, clockTick);
  const hasActiveGenerationJob = isGenerationJobActive(activeJob);
  const isGenerationQueued = isGenerationJobQueued(activeJob);
  const isEditorLocked = isSending || isUploading || isGenerationPreparing;
  const isSendLocked = isEditorLocked || messageCooldownRemainingSeconds > 0;
  const isGenerationActionLocked =
    isSendLocked || hasActiveGenerationJob || isRefreshingQueue;
  const isQueueRefreshLocked =
    !isGenerationQueued || isRefreshingQueue || queueRefreshRemainingSeconds > 0;

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setClockTick(Date.now());
    }, 1000);

    return () => {
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    void getChatHistoryPage(sessionId, { limit: INITIAL_HISTORY_PAGE_SIZE })
      .then((historyPage) => {
        if (!isMounted) {
          return;
        }

        const mergedHistory = mergeHistoryIntoCurrent(messagesRef.current, historyPage.items);
        setMessages(mergedHistory);
        setActiveJob((current) => getLatestGenerationJob(mergedHistory) ?? current);
        setStoredProfile((profile) => extractProfileFromMessages(mergedHistory, profile));
        setHasMoreHistory(historyPage.has_more);
        setNextHistoryCursor(historyPage.next_before_message_id ?? null);
        setBackendState("connected");
        setErrorMessage(null);
        setIsHistoryLoading(false);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }
        setIsHistoryLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [sessionId]);

  useEffect(() => {
    writePersistedChatState(sessionId, {
      messages,
      uploadedAsset,
      activeJob,
    });
  }, [sessionId, messages, uploadedAsset, activeJob]);

  useEffect(() => {
    writeStoredProfile(storedProfile);
  }, [storedProfile]);

  useEffect(() => {
    if (
      !activeJob ||
      activeJob.status === "completed" ||
      activeJob.status === "failed" ||
      activeJob.status === "cancelled"
    ) {
      return;
    }

    let isCancelled = false;

    const syncActiveJob = async () => {
      try {
        const nextJob = await getGenerationJob(activeJob.public_id);
        if (isCancelled) {
          return;
        }
        const mergedJob = mergeQueuedJobState(activeJob, nextJob);
        setBackendState("connected");
        setErrorMessage(null);
        setActiveJob(mergedJob);
        setMessages((current) => syncGenerationJobInMessages(current, mergedJob));
      } catch {
        if (isCancelled) {
          return;
        }
        setBackendState("error");
        setErrorMessage(
          locale === "ru"
            ? "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0442\u0430\u0442\u0443\u0441 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 backend \u0438 ComfyUI."
            : "Could not refresh the generation status. Check the backend and ComfyUI."
        );
      }
    };

    void syncActiveJob();
    const timer = window.setInterval(() => {
      void syncActiveJob();
    }, GENERATION_STATUS_POLL_INTERVAL_MS);

    return () => {
      isCancelled = true;
      window.clearInterval(timer);
    };
  }, [activeJob?.public_id, activeJob?.status, locale]);

  const loadOlderHistory = async () => {
    if (isLoadingOlderHistory || !hasMoreHistory || !nextHistoryCursor) {
      return;
    }

    setIsLoadingOlderHistory(true);
    try {
      const historyPage = await getChatHistoryPage(sessionId, {
        limit: INITIAL_HISTORY_PAGE_SIZE,
        beforeMessageId: nextHistoryCursor,
      });
      setMessages((current) => prependHistoryPage(current, historyPage.items));
      setHasMoreHistory(historyPage.has_more);
      setNextHistoryCursor(historyPage.next_before_message_id ?? null);
      setBackendState("connected");
      setErrorMessage(null);
    } catch {
      setBackendState("error");
      setErrorMessage(
        locale === "ru"
          ? "Не удалось загрузить более ранние сообщения."
          : "Could not load older messages."
      );
    } finally {
      setIsLoadingOlderHistory(false);
    }
  };

  const sendDraft = async ({
    inputOverride,
    uploadedAssetOverride,
    explicitAutoGenerate,
    requestedIntent
  }: {
    inputOverride?: string;
    uploadedAssetOverride?: UploadedAsset | null;
    explicitAutoGenerate?: boolean;
    requestedIntent?: RequestedIntent;
  } = {}) => {
    const draftInput = inputOverride ?? input;
    const draftUploadedAsset = uploadedAssetOverride ?? uploadedAsset;
    if ((!draftInput.trim() && !draftUploadedAsset) || isSendLocked) {
      return;
    }

    const profileFromDraft = mergeStoredProfile(storedProfile, {
      gender: extractGenderFromText(draftInput),
      heightCm: extractHeightCmFromText(draftInput),
      weightKg: extractWeightKgFromText(draftInput),
    });

    const previousActiveJob = activeJob;
    const hasQueuedOrRunningGeneration = isGenerationJobActive(previousActiveJob);
    const autoGenerate = shouldAutoGenerateMessage({
      input: draftInput,
      uploadedAsset: draftUploadedAsset,
      explicitAutoGenerate
    }) && !hasQueuedOrRunningGeneration;
    const effectiveRequestedIntent =
      requestedIntent ?? (draftUploadedAsset ? "garment_matching" : undefined);
    const optimisticMessageId = -Math.floor(Date.now() + Math.random() * 1000);
    const optimisticUserMessage: ChatMessage = {
      id: optimisticMessageId,
      session_id: sessionId,
      role: "user",
      locale,
      content: buildDraftMessage(draftInput, draftUploadedAsset, locale),
      generation_job_id: null,
      uploaded_asset: draftUploadedAsset,
      payload: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    setMessages((current) => [...current, optimisticUserMessage]);
    setInput("");
    setUploadedAsset(null);
    setActiveJob((current) => (autoGenerate && !current ? null : current));
    setIsGenerationPreparing(autoGenerate);
    setIsSending(true);
    setErrorMessage(null);
    setBackendState("connecting");
    setStoredProfile(profileFromDraft);

    try {
      const response = await sendStylistMessage({
        session_id: sessionId,
        locale,
        message: draftInput.trim() || undefined,
        uploaded_asset_id: draftUploadedAsset?.id,
        requested_intent: effectiveRequestedIntent,
        profile_gender: profileFromDraft.gender || undefined,
        body_height_cm: parseOptionalNumber(profileFromDraft.heightCm),
        body_weight_kg: parseOptionalNumber(profileFromDraft.weightKg),
        auto_generate: autoGenerate
      });
      const assistantMessage: ChatMessage = {
        ...response.assistant_message,
        generation_job: response.generation_job ?? null
      };

      setBackendState("connected");
      setMessages((current) => [...current, assistantMessage]);
      setActiveJob(response.generation_job ?? previousActiveJob);
      setIsGenerationPreparing(false);
      setStoredProfile((current) => extractProfileFromMessages([...messages, optimisticUserMessage, assistantMessage], current));
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessageId));
      setInput(draftInput);
      setUploadedAsset(draftUploadedAsset);
      setActiveJob(previousActiveJob);
      setIsGenerationPreparing(false);
      setBackendState("error");
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0432 backend."
            : "Could not send the message to the backend."
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleUpload = async (file: File) => {
    if (isGenerationActionLocked) {
      return;
    }
    setIsUploading(true);
    try {
      const asset = await uploadAsset(file, undefined, "generation_input");
      setBackendState("connected");
      setErrorMessage(null);

      if (getLastAssistantMessage(messages)?.payload?.kind === "upload_request") {
        await sendDraft({
          inputOverride: "",
          uploadedAssetOverride: asset,
          explicitAutoGenerate: true,
          requestedIntent: "garment_matching"
        });
        return;
      }

      setUploadedAsset(asset);
    } catch {
      setBackendState("error");
      setErrorMessage(
        locale === "ru"
          ? "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0444\u043e\u0442\u043e \u043d\u0430 backend."
          : "Could not upload the photo to the backend."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handlePairUpload = async (file: File, message: string) => {
    if (isGenerationActionLocked) {
      return;
    }
    setIsUploading(true);
    try {
      const asset = await uploadAsset(file, undefined, "generation_input");
      setBackendState("connected");
      setErrorMessage(null);
      await sendDraft({
        inputOverride: message,
        uploadedAssetOverride: asset,
        explicitAutoGenerate: true,
        requestedIntent: "garment_matching"
      });
    } catch {
      setBackendState("error");
      setErrorMessage(
        locale === "ru"
          ? "Не удалось загрузить фото вещи на backend."
          : "Could not upload the garment photo to the backend."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    await sendDraft();
  };

  const handleRefreshQueuePosition = async () => {
    if (!activeJob || activeJob.status !== "pending" || isQueueRefreshLocked) {
      return;
    }

    setIsRefreshingQueue(true);
    try {
      const nextJob = await refreshGenerationJobQueue(activeJob.public_id);
      const mergedJob = mergeQueuedJobState(activeJob, nextJob);
      setBackendState("connected");
      setErrorMessage(null);
      setActiveJob(mergedJob);
      setMessages((current) => syncGenerationJobInMessages(current, mergedJob));
    } catch (error) {
      setBackendState("error");
      const detail = getErrorPayloadDetail(error);
      if (detail?.next_available_at && typeof detail.next_available_at === "string") {
        const retryAfterSeconds =
          typeof detail.retry_after_seconds === "number" ? detail.retry_after_seconds : null;
        setActiveJob((current) =>
          current
            ? {
                ...current,
                queue_refresh_available_at: detail.next_available_at as string,
                queue_refresh_retry_after_seconds: retryAfterSeconds,
              }
            : current
        );
      }
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось обновить позицию в очереди."
            : "Could not refresh the queue position."
      );
    } finally {
      setIsRefreshingQueue(false);
    }
  };

  const handleQuickAction = async (
    message: string,
    explicitAutoGenerate = false,
    requestedIntent?: RequestedIntent
  ) => {
    await sendDraft({
      inputOverride: message,
      uploadedAssetOverride: null,
      explicitAutoGenerate,
      requestedIntent
    });
  };

  return {
    sessionId,
    messages,
    input,
    setInput,
    uploadedAsset,
    activeJob,
    isHistoryLoading,
    isLoadingOlderHistory,
    hasMoreHistory,
    isSending,
    isUploading,
    isGenerationPreparing,
    isInputLocked: isSendLocked,
    isSendLocked,
    isEditorLocked,
    isGenerationActionLocked,
    isGenerationQueued,
    hasActiveGenerationJob,
    messageCooldownRemainingSeconds,
    queueRefreshRemainingSeconds,
    isRefreshingQueue,
    isChatOffline: false,
    chatAvailability,
    backendState,
    errorMessage,
    loadOlderHistory,
    handleUpload,
    handlePairUpload,
    handleRefreshQueuePosition,
    handleSend,
    handleQuickAction
  };
}
