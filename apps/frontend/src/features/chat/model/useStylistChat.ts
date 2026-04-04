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
  profileGender: string;
  bodyHeightCm: string;
  bodyWeightKg: string;
  autoGenerate: boolean;
};

type BackendState = "connecting" | "connected" | "error";

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
      cooldownUntil: typeof parsed.cooldownUntil === "number" ? parsed.cooldownUntil : null,
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
  const [profileGender, setProfileGender] = useState(() => persistedState?.profileGender ?? "");
  const [bodyHeightCm, setBodyHeightCm] = useState(() => persistedState?.bodyHeightCm ?? "");
  const [bodyWeightKg, setBodyWeightKg] = useState(() => persistedState?.bodyWeightKg ?? "");
  const [autoGenerate, setAutoGenerate] = useState(() => persistedState?.autoGenerate ?? true);
  const [activeJob, setActiveJob] = useState<GenerationJob | null>(
    () => persistedState?.activeJob ?? getLatestGenerationJob(persistedState?.messages ?? [])
  );
  const [isHistoryLoading, setIsHistoryLoading] = useState(() => !persistedState);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [backendState, setBackendState] = useState<BackendState>(() => (persistedState ? "connected" : "connecting"));
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [cooldownUntil, setCooldownUntil] = useState<number | null>(
    () => persistedState?.cooldownUntil ?? getCooldownUntil(persistedState?.messages ?? [])
  );
  const [cooldownRemainingMs, setCooldownRemainingMs] = useState(0);
  const [isGenerationPreparing, setIsGenerationPreparing] = useState(false);
  const [pendingProfileFields, setPendingProfileFields] = useState<ProfileField[]>(
    () => getPendingProfileFields(persistedState?.messages ?? [])
  );

  const syncHistory = useCallback((history: ChatMessage[]) => {
    setMessages(history);
    setCooldownUntil(getCooldownUntil(history));
    setActiveJob(getLatestGenerationJob(history));
    setPendingProfileFields(getPendingProfileFields(history));
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
        if (isMounted) {
          setBackendState("error");
          setErrorMessage(
            locale === "ru"
              ? "Нет ответа от backend. Проверьте API и логи контейнера backend."
              : "The backend is not responding. Check the API and backend container logs."
          );
          setIsHistoryLoading(false);
        }
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
      cooldownUntil,
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
    cooldownUntil,
    profileGender,
    bodyHeightCm,
    bodyWeightKg,
    autoGenerate
  ]);

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
            ? "Не удалось обновить статус генерации. Проверьте backend и ComfyUI."
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
          ? "Не удалось загрузить файл на backend."
          : "Could not upload the file to the backend."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleSend = async () => {
    const profileDraftExists = hasProfileDraft(profileGender, bodyHeightCm, bodyWeightKg);
    if ((!input.trim() && !uploadedAsset && !profileDraftExists) || cooldownRemainingMs > 0) {
      return;
    }

    const draftInput = input;
    const draftUploadedAsset = uploadedAsset;
    const draftProfileGender = profileGender;
    const draftBodyHeightCm = bodyHeightCm;
    const draftBodyWeightKg = bodyWeightKg;
    const draftAutoGenerate = autoGenerate;
    const draftProfileSummary = buildProfileSummary(locale, draftProfileGender, draftBodyHeightCm, draftBodyWeightKg);
    const previousCooldownUntil = cooldownUntil;
    const previousActiveJob = activeJob;
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
    setCooldownUntil(Date.now() + MESSAGE_COOLDOWN_MS);
    setCooldownRemainingMs(MESSAGE_COOLDOWN_MS);
    setInput("");
    setUploadedAsset(null);
    setActiveJob(null);
    setIsGenerationPreparing(draftAutoGenerate);
    setIsSending(true);
    setErrorMessage(null);
    setBackendState("connecting");

    try {
      const response = await sendStylistMessage({
        session_id: sessionId,
        locale,
        message: draftInput.trim() || (!draftUploadedAsset && draftProfileSummary ? draftProfileSummary : undefined),
        uploaded_asset_id: draftUploadedAsset?.id,
        profile_gender: draftProfileGender || undefined,
        body_height_cm: parseOptionalNumber(draftBodyHeightCm),
        body_weight_kg: parseOptionalNumber(draftBodyWeightKg),
        auto_generate: draftAutoGenerate
      });
      const assistantMessage: ChatMessage = {
        ...response.assistant_message,
        generation_job: response.generation_job ?? null
      };

      setBackendState("connected");
      setMessages((current) => [...current, assistantMessage]);
      setPendingProfileFields((assistantMessage.payload?.missing_profile_fields as ProfileField[] | undefined) ?? []);
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
    isSending,
    isUploading,
    isGenerationPreparing,
    backendState,
    errorMessage,
    pendingProfileFields,
    cooldownRemainingMs,
    messageCooldownMs: MESSAGE_COOLDOWN_MS,
    handleUpload,
    handleSend
  };
}
