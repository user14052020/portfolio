"use client";

import { useEffect, useRef, useState } from "react";

import type { CommandName } from "@/entities/command/model/types";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import type { GenerationJobState } from "@/entities/generation-job/model/types";
import { attachGarmentAsset } from "@/features/attach-garment-asset/model/attachGarmentAsset";
import { submitFollowupClarification } from "@/features/followup-clarification/model/submitFollowupClarification";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
  runQuickActionCommand,
} from "@/features/run-chat-command/model/runChatCommand";
import {
  buildFreeformMessagePayload,
  sendFreeformMessage,
} from "@/features/send-chat-message/model/sendChatMessage";
import { retryGeneration } from "@/features/retry-generation/model/retryGeneration";
import { chatGateway } from "@/shared/api/gateways/chatGateway";
import { generationGateway } from "@/shared/api/gateways/generationGateway";
import { sessionContextGateway } from "@/shared/api/gateways/sessionContextGateway";
import type { Locale, UploadedAsset } from "@/shared/api/types";

import {
  createClientMessageId,
  createDefaultScenarioContext,
  createOptimisticUserMessage,
  createSessionId,
  GENERATION_STATUS_POLL_INTERVAL_MS,
  getComposerMessageSource,
  getInitialVisibleMessages,
  getLatestGenerationJob,
  INITIAL_HISTORY_PAGE_SIZE,
  isGenerationJobActive,
  isGenerationJobQueued,
  mergeHistoryIntoCurrent,
  mergeQueuedJobState,
  prependHistoryPage,
  readPersistedStylistChatUiState,
  syncGenerationJobInMessages,
  writePersistedStylistChatUiState,
} from "./lib";

type BackendState = "connecting" | "connected" | "error";
type ChatAvailability = "online" | "offline";

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

function getRemainingSeconds(endsAt: number | null, now: number) {
  if (!endsAt) {
    return 0;
  }

  return Math.max(0, Math.ceil((endsAt - now) / 1000));
}

export function useStylistChatProcess(locale: Locale) {
  const [bootstrap] = useState(() => {
    const nextSessionId = createSessionId();
    const persistedState = readPersistedStylistChatUiState(nextSessionId);
    return {
      sessionId: nextSessionId,
      persistedState: persistedState
        ? {
            ...persistedState,
            messages: getInitialVisibleMessages(persistedState.messages),
          }
        : null,
    };
  });
  const sessionId = bootstrap.sessionId;
  const persistedState = bootstrap.persistedState;

  const [messages, setMessages] = useState<ThreadMessage[]>(() => persistedState?.messages ?? []);
  const [input, setInput] = useState("");
  const [uploadedAsset, setUploadedAsset] = useState<UploadedAsset | null>(
    () => persistedState?.uploadedAsset ?? null
  );
  const [activeJob, setActiveJob] = useState<GenerationJobState | null>(
    () => persistedState?.activeJob ?? getLatestGenerationJob(persistedState?.messages ?? [])
  );
  const [scenarioContext, setScenarioContext] = useState<FrontendScenarioContext>(
    createDefaultScenarioContext()
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
  const [clockTick, setClockTick] = useState(() => Date.now());
  const messagesRef = useRef(messages);
  const chatAvailability: ChatAvailability = backendState === "error" ? "offline" : "online";
  const queueRefreshAvailableAt = activeJob?.queue_refresh_available_at
    ? Date.parse(activeJob.queue_refresh_available_at)
    : null;
  const queueRefreshRemainingSeconds = getRemainingSeconds(queueRefreshAvailableAt, clockTick);
  const hasActiveGenerationJob = isGenerationJobActive(activeJob);
  const isGenerationQueued = isGenerationJobQueued(activeJob);
  const isEditorLocked = isSending || isUploading;
  const canSubmitDraft = Boolean(input.trim() || uploadedAsset);
  const isSendLocked = isEditorLocked || !canSubmitDraft;
  const isGenerationActionLocked = isSending || isUploading || isRefreshingQueue;

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

    const loadInitialState = async () => {
      try {
        const [historyPage, context] = await Promise.all([
          chatGateway.getHistoryPage(sessionId, { limit: INITIAL_HISTORY_PAGE_SIZE }),
          sessionContextGateway.getContext(sessionId),
        ]);
        if (!isMounted) {
          return;
        }

        const mergedHistory = mergeHistoryIntoCurrent(messagesRef.current, historyPage.items as ThreadMessage[]);
        const latestJob = getLatestGenerationJob(mergedHistory);

        setMessages(mergedHistory);
        setScenarioContext(context);
        setActiveJob(latestJob);
        setHasMoreHistory(historyPage.has_more);
        setNextHistoryCursor(historyPage.next_before_message_id ?? null);
        setBackendState("connected");
        setErrorMessage(null);
        setIsHistoryLoading(false);

        if (!latestJob && context.currentJobId) {
          const currentJob = await generationGateway.getStatus(context.currentJobId);
          if (!isMounted) {
            return;
          }
          setActiveJob(currentJob);
          setMessages((current) => syncGenerationJobInMessages(current, currentJob));
        }
      } catch (error) {
        if (!isMounted) {
          return;
        }
        setBackendState("error");
        setErrorMessage(
          error instanceof Error && error.message
            ? error.message
            : locale === "ru"
              ? "Не удалось загрузить состояние чата."
              : "Could not load the chat state."
        );
        setIsHistoryLoading(false);
      }
    };

    void loadInitialState();

    return () => {
      isMounted = false;
    };
  }, [sessionId, locale]);

  useEffect(() => {
    writePersistedStylistChatUiState(sessionId, {
      messages,
      uploadedAsset,
      activeJob,
    });
  }, [sessionId, messages, uploadedAsset, activeJob]);

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
        const nextJob = await generationGateway.getStatus(activeJob.public_id);
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
            ? "Не удалось обновить статус генерации."
            : "Could not refresh the generation status."
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
      const historyPage = await chatGateway.getHistoryPage(sessionId, {
        limit: INITIAL_HISTORY_PAGE_SIZE,
        beforeMessageId: nextHistoryCursor,
      });
      setMessages((current) => prependHistoryPage(current, historyPage.items as ThreadMessage[]));
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

  const handleServerResponse = ({
    response,
    previousActiveJob,
  }: {
    response: Awaited<ReturnType<typeof sendFreeformMessage>>;
    previousActiveJob: GenerationJobState | null;
  }) => {
    setBackendState("connected");
    setErrorMessage(null);
    setScenarioContext(response.context);
    setMessages((current) => [...current, response.assistantMessage]);
    setActiveJob(response.generationJob ?? previousActiveJob);
  };

  const runQuickAction = async (actionId: CommandName) => {
    if (isGenerationActionLocked) {
      return;
    }

    const action = getQuickActionDefinitions(locale).find((item) => item.id === actionId);
    if (!action) {
      return;
    }

    const previousActiveJob = activeJob;
    setIsSending(true);
    setBackendState("connecting");
    setErrorMessage(null);

    try {
      const response = await runQuickActionCommand(
        buildQuickActionCommandPayload({
          sessionId,
          locale,
          action,
          assetId: uploadedAsset?.id ?? null,
          clientMessageId: createClientMessageId(),
        })
      );

      setUploadedAsset(null);
      handleServerResponse({ response, previousActiveJob });
    } catch (error) {
      setBackendState("error");
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось запустить команду."
            : "Could not run the command."
      );
    } finally {
      setIsSending(false);
    }
  };

  const sendComposerMessage = async () => {
    if (isSendLocked) {
      return;
    }

    const draftInput = input;
    const draftUploadedAsset = uploadedAsset;
    const previousActiveJob = activeJob;
    const optimisticMessage = createOptimisticUserMessage({
      sessionId,
      locale,
      input: draftInput,
      uploadedAsset: draftUploadedAsset,
    });
    const composerSource = getComposerMessageSource(scenarioContext);
    const clientMessageId = createClientMessageId();

    setMessages((current) => [...current, optimisticMessage]);
    setInput("");
    setUploadedAsset(null);
    setIsSending(true);
    setBackendState("connecting");
    setErrorMessage(null);

    try {
      const response =
        composerSource === "followup"
          ? await submitFollowupClarification({
              sessionId,
              locale,
              message: draftInput.trim() || null,
              assetId: draftUploadedAsset?.id ?? null,
              clientMessageId,
            })
          : await sendFreeformMessage(
              buildFreeformMessagePayload({
                sessionId,
                locale,
                message: draftInput.trim() || null,
                assetId: draftUploadedAsset?.id ?? null,
                clientMessageId,
              })
            );

      handleServerResponse({ response, previousActiveJob });
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessage.id));
      setInput(draftInput);
      setUploadedAsset(draftUploadedAsset);
      setBackendState("error");
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось отправить сообщение."
            : "Could not send the message."
      );
    } finally {
      setIsSending(false);
    }
  };

  const handleAttachAsset = async (file: File) => {
    if (isSending || isUploading) {
      return;
    }

    setIsUploading(true);
    try {
      const asset = await attachGarmentAsset(file);
      setUploadedAsset(asset);
      setBackendState("connected");
      setErrorMessage(null);
    } catch (error) {
      setBackendState("error");
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось загрузить фото вещи."
            : "Could not upload the garment photo."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const refreshGenerationStatus = async () => {
    if (!activeJob || activeJob.status !== "pending" || isRefreshingQueue) {
      return;
    }

    setIsRefreshingQueue(true);
    try {
      const nextJob = await retryGeneration(activeJob.public_id);
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
            ? "Не удалось обновить очередь генерации."
            : "Could not refresh the generation queue."
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
    uploadedAsset,
    clearUploadedAsset: () => setUploadedAsset(null),
    scenarioContext,
    activeJob,
    isHistoryLoading,
    isLoadingOlderHistory,
    hasMoreHistory,
    isSending,
    isUploading,
    isEditorLocked,
    isSendLocked,
    isGenerationActionLocked,
    isRefreshingQueue,
    hasActiveGenerationJob,
    isGenerationQueued,
    queueRefreshRemainingSeconds,
    backendState,
    chatAvailability,
    errorMessage,
    loadOlderHistory,
    runQuickAction,
    sendComposerMessage,
    handleAttachAsset,
    refreshGenerationStatus,
  };
}
