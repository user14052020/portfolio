"use client";

import { useCallback, useEffect, useState } from "react";

import { getChatHistory, getGenerationJob, sendStylistMessage, uploadAsset } from "@/shared/api/client";
import type { ChatMessage, GenerationJob, Locale, UploadedAsset } from "@/shared/api/types";

const MESSAGE_COOLDOWN_MS = 60_000;
const SESSION_STORAGE_KEY = "portfolio-chat-session";
const CHAT_STATE_STORAGE_KEY_PREFIX = "portfolio-chat-state";

type PersistedChatState = {
  messages: ChatMessage[];
  uploadedAsset: UploadedAsset | null;
  activeJob: GenerationJob | null;
  cooldownUntil: number | null;
};

type BackendState = "connecting" | "connected" | "error";

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
      cooldownUntil: typeof parsed.cooldownUntil === "number" ? parsed.cooldownUntil : null
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

function getLastUserMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "user");
}

function getLastAssistantMessage(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.role === "assistant");
}

function isProfileClarificationMessage(message: ChatMessage | undefined) {
  return message?.role === "assistant" && message.payload?.kind === "profile_clarification";
}

function getCooldownUntil(messages: ChatMessage[]) {
  const lastUserMessage = getLastUserMessage(messages);
  if (!lastUserMessage) {
    return null;
  }

  const lastAssistantMessage = getLastAssistantMessage(messages);
  if (
    isProfileClarificationMessage(lastAssistantMessage) &&
    new Date(lastAssistantMessage.created_at).getTime() >= new Date(lastUserMessage.created_at).getTime()
  ) {
    return null;
  }

  const createdAt = new Date(lastUserMessage.created_at).getTime();
  if (!Number.isFinite(createdAt)) {
    return null;
  }

  const nextAvailableAt = createdAt + MESSAGE_COOLDOWN_MS;
  return nextAvailableAt > Date.now() ? nextAvailableAt : null;
}

function getLatestGenerationJob(messages: ChatMessage[]) {
  return (
    [...messages]
      .reverse()
      .find((message) => message.role === "assistant" && message.generation_job)?.generation_job ?? null
  );
}

function buildDraftMessage(input: string, uploadedAsset: UploadedAsset | null) {
  const trimmedInput = input.trim();
  if (trimmedInput) {
    return trimmedInput;
  }

  if (uploadedAsset) {
    return `Uploaded wardrobe item: ${uploadedAsset.original_filename}`;
  }

  return "Need a new styled outfit";
}

export function useStylistChat(locale: Locale) {
  const [bootstrap] = useState(() => {
    const nextSessionId = createSessionId();
    return {
      sessionId: nextSessionId,
      persistedState: readPersistedChatState(nextSessionId)
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
  const [isHistoryLoading, setIsHistoryLoading] = useState(() => !persistedState);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGenerationPreparing, setIsGenerationPreparing] = useState(false);
  const [backendState, setBackendState] = useState<BackendState>(() =>
    persistedState ? "connected" : "connecting"
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(
    () => persistedState?.cooldownUntil ?? getCooldownUntil(persistedState?.messages ?? [])
  );
  const [cooldownRemainingMs, setCooldownRemainingMs] = useState(0);

  const syncHistory = useCallback((history: ChatMessage[]) => {
    setMessages(history);
    setCooldownUntil(getCooldownUntil(history));
    setActiveJob(getLatestGenerationJob(history));
  }, []);

  useEffect(() => {
    let isMounted = true;
    setBackendState("connecting");

    getChatHistory(sessionId)
      .then((history) => {
        if (!isMounted) {
          return;
        }

        syncHistory(history);
        setBackendState("connected");
        setErrorMessage(null);
        setIsHistoryLoading(false);
      })
      .catch(() => {
        if (!isMounted) {
          return;
        }

        setBackendState("error");
        setErrorMessage(
          locale === "ru"
            ? "\u041d\u0435\u0442 \u043e\u0442\u0432\u0435\u0442\u0430 \u043e\u0442 backend. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 API \u0438 \u043b\u043e\u0433\u0438 \u043a\u043e\u043d\u0442\u0435\u0439\u043d\u0435\u0440\u0430 backend."
            : "The backend is not responding. Check the API and backend container logs."
        );
        setIsHistoryLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [locale, sessionId, syncHistory]);

  useEffect(() => {
    writePersistedChatState(sessionId, {
      messages,
      uploadedAsset,
      activeJob,
      cooldownUntil
    });
  }, [sessionId, messages, uploadedAsset, activeJob, cooldownUntil]);

  useEffect(() => {
    if (!cooldownUntil) {
      setCooldownRemainingMs(0);
      return;
    }

    const updateCooldown = () => {
      const remaining = Math.max(0, cooldownUntil - Date.now());
      setCooldownRemainingMs(remaining);
      if (remaining === 0) {
        setCooldownUntil(null);
      }
    };

    updateCooldown();
    const timer = window.setInterval(updateCooldown, 250);
    return () => window.clearInterval(timer);
  }, [cooldownUntil]);

  useEffect(() => {
    if (!activeJob || activeJob.status === "completed" || activeJob.status === "failed") {
      return;
    }

    const timer = window.setInterval(async () => {
      try {
        const nextJob = await getGenerationJob(activeJob.public_id);
        setBackendState("connected");
        setErrorMessage(null);
        setActiveJob(nextJob);
        setMessages((current) =>
          current.map((message) =>
            message.generation_job?.public_id === nextJob.public_id ? { ...message, generation_job: nextJob } : message
          )
        );
      } catch {
        setBackendState("error");
        setErrorMessage(
          locale === "ru"
            ? "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0431\u043d\u043e\u0432\u0438\u0442\u044c \u0441\u0442\u0430\u0442\u0443\u0441 \u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u0438. \u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 backend \u0438 ComfyUI."
            : "Could not refresh the generation status. Check the backend and ComfyUI."
        );
      }
    }, 5000);

    return () => window.clearInterval(timer);
  }, [activeJob, locale]);

  const handleUpload = async (file: File) => {
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
          ? "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0444\u0430\u0439\u043b \u043d\u0430 backend."
          : "Could not upload the file to the backend."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    if ((!input.trim() && !uploadedAsset) || cooldownRemainingMs > 0) {
      return;
    }

    const draftInput = input;
    const draftUploadedAsset = uploadedAsset;
    const previousCooldownUntil = cooldownUntil;
    const previousActiveJob = activeJob;
    const optimisticMessageId = -Math.floor(Date.now() + Math.random() * 1000);
    const optimisticUserMessage: ChatMessage = {
      id: optimisticMessageId,
      session_id: sessionId,
      role: "user",
      locale,
      content: buildDraftMessage(draftInput, draftUploadedAsset),
      generation_job_id: null,
      uploaded_asset: draftUploadedAsset,
      payload: {},
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    setMessages((current) => [...current, optimisticUserMessage]);
    setCooldownUntil(Date.now() + MESSAGE_COOLDOWN_MS);
    setCooldownRemainingMs(MESSAGE_COOLDOWN_MS);
    setInput("");
    setUploadedAsset(null);
    setActiveJob(null);
    setIsGenerationPreparing(true);
    setIsSending(true);
    setErrorMessage(null);
    setBackendState("connecting");

    try {
      const response = await sendStylistMessage({
        session_id: sessionId,
        locale,
        message: draftInput.trim() || undefined,
        uploaded_asset_id: draftUploadedAsset?.id,
        auto_generate: true
      });
      const assistantMessage: ChatMessage = {
        ...response.assistant_message,
        generation_job: response.generation_job ?? null
      };

      setBackendState("connected");
      setMessages((current) => [...current, assistantMessage]);
      setActiveJob(response.generation_job ?? null);
      setIsGenerationPreparing(false);

      if (assistantMessage.payload?.kind === "profile_clarification") {
        setCooldownUntil(null);
        setCooldownRemainingMs(0);
      }
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessageId));
      setInput(draftInput);
      setUploadedAsset(draftUploadedAsset);
      setActiveJob(previousActiveJob);
      setIsGenerationPreparing(false);
      setBackendState("error");

      const payload =
        error && typeof error === "object" && "payload" in error
          ? (error as { payload?: { detail?: { retry_after_seconds?: number } } }).payload
          : undefined;
      const retryAfterSeconds = payload?.detail?.retry_after_seconds;
      if (typeof retryAfterSeconds === "number" && retryAfterSeconds > 0) {
        setCooldownUntil(Date.now() + retryAfterSeconds * 1000);
        setCooldownRemainingMs(retryAfterSeconds * 1000);
      } else {
        setCooldownUntil(previousCooldownUntil);
        setCooldownRemainingMs(previousCooldownUntil ? Math.max(0, previousCooldownUntil - Date.now()) : 0);
      }

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

  return {
    sessionId,
    messages,
    input,
    setInput,
    uploadedAsset,
    activeJob,
    isHistoryLoading,
    isSending,
    isUploading,
    isGenerationPreparing,
    backendState,
    errorMessage,
    cooldownRemainingMs,
    messageCooldownMs: MESSAGE_COOLDOWN_MS,
    handleUpload,
    handleSend
  };
}
