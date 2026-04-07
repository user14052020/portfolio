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
const GENERATION_STATUS_POLL_INTERVAL_MS = 10000;
const INITIAL_HISTORY_PAGE_SIZE = 5;
const MESSAGE_COOLDOWN_SECONDS = 60;

type PersistedChatState = {
  messages: ChatMessage[];
  uploadedAsset: UploadedAsset | null;
  activeJob: GenerationJob | null;
  profileGender: string;
  bodyHeightCm: string;
  bodyWeightKg: string;
  autoGenerate: boolean;
};

type BackendState = "connecting" | "connected" | "error";
type ChatAvailability = "online" | "offline";

type ProfileField = "gender" | "height_cm" | "weight_kg";

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
      profileGender: typeof parsed.profileGender === "string" ? parsed.profileGender : "",
      bodyHeightCm: typeof parsed.bodyHeightCm === "string" ? parsed.bodyHeightCm : "",
      bodyWeightKg: typeof parsed.bodyWeightKg === "string" ? parsed.bodyWeightKg : "",
      autoGenerate: typeof parsed.autoGenerate === "boolean" ? parsed.autoGenerate : true
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
    // Ignore storage errors so chat remains usable even in restricted browsers.
  }
}

function getLastAssistantMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "assistant");
}

function isProfileClarificationMessage(message: ChatMessage | undefined) {
  return message?.role === "assistant" && message.payload?.kind === "profile_clarification";
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

function getPendingProfileFields(messages: ChatMessage[]): ProfileField[] {
  const lastAssistantMessage = getLastAssistantMessage(messages);
  if (!isProfileClarificationMessage(lastAssistantMessage)) {
    return [];
  }

  const rawFields = lastAssistantMessage.payload?.missing_profile_fields;
  return Array.isArray(rawFields)
    ? rawFields.filter(
        (value): value is ProfileField =>
          value === "gender" || value === "height_cm" || value === "weight_kg"
      )
    : [];
}

function normalizeNumberInput(value: string) {
  return value.replace(/[^\d]/g, "").slice(0, 3);
}

function parseOptionalNumber(value: string) {
  if (!value.trim()) {
    return undefined;
  }

  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function hasProfileDraft(profileGender: string, bodyHeightCm: string, bodyWeightKg: string) {
  return Boolean(profileGender || bodyHeightCm.trim() || bodyWeightKg.trim());
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

function buildProfileSummary(
  locale: Locale,
  profileGender: string,
  bodyHeightCm: string,
  bodyWeightKg: string
) {
  const parts: string[] = [];

  if (profileGender === "male") {
    parts.push(locale === "ru" ? "мужчина" : "male");
  } else if (profileGender === "female") {
    parts.push(locale === "ru" ? "женщина" : "female");
  }

  if (bodyHeightCm.trim()) {
    parts.push(locale === "ru" ? `${bodyHeightCm.trim()} см` : `${bodyHeightCm.trim()} cm`);
  }

  if (bodyWeightKg.trim()) {
    parts.push(locale === "ru" ? `${bodyWeightKg.trim()} кг` : `${bodyWeightKg.trim()} kg`);
  }

  return parts.join(", ");
}

function buildDraftMessage(
  input: string,
  uploadedAsset: UploadedAsset | null,
  locale: Locale,
  profileGender: string,
  bodyHeightCm: string,
  bodyWeightKg: string
) {
  const trimmedInput = input.trim();
  if (trimmedInput) {
    return trimmedInput;
  }
  if (uploadedAsset) {
    return `Uploaded wardrobe item: ${uploadedAsset.original_filename}`;
  }
  const profileSummary = buildProfileSummary(locale, profileGender, bodyHeightCm, bodyWeightKg);
  if (profileSummary) {
    return profileSummary;
  }
  return "Need a new styled outfit";
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
  const [profileGender, setProfileGender] = useState(() => persistedState?.profileGender ?? "");
  const [bodyHeightCm, setBodyHeightCm] = useState(() => persistedState?.bodyHeightCm ?? "");
  const [bodyWeightKg, setBodyWeightKg] = useState(() => persistedState?.bodyWeightKg ?? "");
  const [autoGenerate, setAutoGenerate] = useState(() => persistedState?.autoGenerate ?? true);
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(
    () => persistedState?.activeJob ?? getLatestGenerationJob(persistedState?.messages ?? [])
  );
  const [isHistoryLoading, setIsHistoryLoading] = useState(messages.length === 0);
  const [isLoadingOlderHistory, setIsLoadingOlderHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [nextHistoryCursor, setNextHistoryCursor] = useState<number | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshingQueue, setIsRefreshingQueue] = useState(false);
  const [backendState, setBackendState] = useState<BackendState>("connected");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isGenerationPreparing, setIsGenerationPreparing] = useState(false);
  const [pendingProfileFields, setPendingProfileFields] = useState<ProfileField[]>(
    () => getPendingProfileFields(persistedState?.messages ?? [])
  );
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
  const isGenerationActionLocked = isSendLocked || hasActiveGenerationJob || isRefreshingQueue;
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
        setPendingProfileFields(getPendingProfileFields(mergedHistory));
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
      profileGender,
      bodyHeightCm,
      bodyWeightKg,
      autoGenerate
    });
  }, [
    sessionId,
    messages,
    uploadedAsset,
    activeJob,
    profileGender,
    bodyHeightCm,
    bodyWeightKg,
    autoGenerate
  ]);

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
            ? "Не удалось обновить статус генерации. Проверьте backend и ComfyUI."
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

  const handleUpload = async (file: File) => {
    if (isGenerationActionLocked) {
      return;
    }
    setIsUploading(true);
    try {
      const asset = await uploadAsset(file, undefined, "generation_input");
      setBackendState("connected");
      setErrorMessage(null);
      setUploadedAsset(asset);
    } catch {
      setBackendState("error");
      setErrorMessage(
        locale === "ru"
          ? "Не удалось загрузить файл на backend."
          : "Could not upload the file to the backend."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    const profileDraftExists = hasProfileDraft(profileGender, bodyHeightCm, bodyWeightKg);
    if ((!input.trim() && !uploadedAsset && !profileDraftExists) || isSendLocked) {
      return;
    }

    const draftInput = input;
    const draftUploadedAsset = uploadedAsset;
    const draftProfileGender = profileGender;
    const draftBodyHeightCm = bodyHeightCm;
    const draftBodyWeightKg = bodyWeightKg;
    const draftAutoGenerate = autoGenerate;
    const draftProfileSummary = buildProfileSummary(locale, draftProfileGender, draftBodyHeightCm, draftBodyWeightKg);
    const requestedIntent = draftUploadedAsset ? "garment_matching" : undefined;
    const previousActiveJob = activeJob;
    const hasQueuedOrRunningGeneration = isGenerationJobActive(previousActiveJob);
    const optimisticMessageId = -Math.floor(Date.now() + Math.random() * 1000);
    const optimisticUserMessage: ChatMessage = {
      id: optimisticMessageId,
      session_id: sessionId,
      role: "user",
      locale,
      content: buildDraftMessage(
        draftInput,
        draftUploadedAsset,
        locale,
        draftProfileGender,
        draftBodyHeightCm,
        draftBodyWeightKg
      ),
      generation_job_id: null,
      uploaded_asset: draftUploadedAsset,
      payload: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    setMessages((current) => [...current, optimisticUserMessage]);
    setInput("");
    setUploadedAsset(null);
    setActiveJob(previousActiveJob);
    setIsGenerationPreparing(draftAutoGenerate && !hasQueuedOrRunningGeneration);
    setIsSending(true);
    setErrorMessage(null);
    setBackendState("connecting");

    try {
      const response = await sendStylistMessage({
        session_id: sessionId,
        locale,
        message: draftInput.trim() || (!draftUploadedAsset && draftProfileSummary ? draftProfileSummary : undefined),
        uploaded_asset_id: draftUploadedAsset?.id,
        requested_intent: requestedIntent,
        profile_gender: draftProfileGender || undefined,
        body_height_cm: parseOptionalNumber(draftBodyHeightCm),
        body_weight_kg: parseOptionalNumber(draftBodyWeightKg),
        auto_generate: draftAutoGenerate && !hasQueuedOrRunningGeneration
      });
      const assistantMessage: ChatMessage = {
        ...response.assistant_message,
        generation_job: response.generation_job ?? null
      };

      setBackendState("connected");
      setMessages((current) => [...current, assistantMessage]);
      setPendingProfileFields((assistantMessage.payload?.missing_profile_fields as ProfileField[] | undefined) ?? []);
      setActiveJob(response.generation_job ?? previousActiveJob);
      setIsGenerationPreparing(false);
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessageId));
      setInput(draftInput);
      setUploadedAsset(draftUploadedAsset);
      setActiveJob(previousActiveJob);
      setIsGenerationPreparing(false);
      setBackendState("error");
      const errorMessageText =
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось отправить сообщение в backend."
            : "Could not send the message to the backend.";
      setErrorMessage(errorMessageText);
    } finally {
      setIsSending(false);
    }
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

  return {
    sessionId,
    messages,
    input,
    setInput,
    profileGender,
    setProfileGender,
    bodyHeightCm,
    setBodyHeightCm: (value: string) => setBodyHeightCm(normalizeNumberInput(value)),
    bodyWeightKg,
    setBodyWeightKg: (value: string) => setBodyWeightKg(normalizeNumberInput(value)),
    autoGenerate,
    setAutoGenerate,
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
    pendingProfileFields,
    loadOlderHistory,
    handleUpload,
    handleRefreshQueuePosition,
    handleSend
  };
}
