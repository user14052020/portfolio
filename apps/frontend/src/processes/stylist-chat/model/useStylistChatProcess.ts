"use client";

import { useEffect, useRef, useState } from "react";

import type { CommandName } from "@/entities/command/model/types";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import {
  extractProfileUpdateFromClarification,
  mergeProfileContext,
  readStoredProfileContext,
  writeStoredProfileContext,
} from "@/entities/profile/model/profileContext";
import type { FrontendProfileContext } from "@/entities/profile/model/types";
import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";
import type { GenerationJobState } from "@/entities/generation-job/model/types";
import type { VisualizationOfferState } from "@/entities/visualization-offer/model/types";
import { attachGarmentAsset } from "@/features/attach-garment-asset/model/attachGarmentAsset";
import { requestVisualization } from "@/features/chat-request-visualization/model/requestVisualization";
import { submitFollowupClarification } from "@/features/followup-clarification/model/submitFollowupClarification";
import { getQuickActionDefinitions } from "@/features/run-chat-command/model/runChatCommand";
import { runStyleExplorationCommand } from "@/features/run-style-exploration-command/model/runStyleExplorationCommand";
import {
  buildFreeformMessagePayload,
  sendFreeformMessage,
} from "@/features/send-chat-message/model/sendChatMessage";
import { retryGeneration } from "@/features/retry-generation/model/retryGeneration";
import { retryStyleExploration } from "@/features/retry-style-exploration/model/retryStyleExploration";
import { chatGateway } from "@/shared/api/gateways/chatGateway";
import { generationGateway } from "@/shared/api/gateways/generationGateway";
import { sessionContextGateway } from "@/shared/api/gateways/sessionContextGateway";
import type { ChatRuntimePolicyState, Locale, UploadedAsset } from "@/shared/api/types";

import {
  createClientMessageId,
  createDefaultScenarioContext,
  createOptimisticUserMessage,
  createSessionId,
  GENERATION_STATUS_POLL_INTERVAL_MS,
  getComposerMessageSource,
  getInitialVisibleMessages,
  getLatestGenerationJob,
  getLatestVisualizationOffer,
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
type ChatCooldownActionType = "message" | "try_other_style";

type ChatCooldownState = {
  actionType: ChatCooldownActionType;
  endsAt: number;
  cooldownSeconds: number;
};

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

function resolveCooldownActionType(detail: Record<string, unknown>): ChatCooldownActionType | null {
  if (detail.action_type === "message" || detail.action_type === "try_other_style") {
    return detail.action_type;
  }
  if (detail.code === "message_cooldown") {
    return "message";
  }
  if (detail.code === "try_other_style_cooldown") {
    return "try_other_style";
  }
  return null;
}

function createEmptyVisualizationOffer(): VisualizationOfferState {
  return {
    canOfferVisualization: false,
    ctaText: null,
    visualizationType: null,
  };
}

export function useStylistChatProcess(
  locale: Locale,
  cooldownConfig: {
    messageCooldownSeconds: number;
    tryOtherStyleCooldownSeconds: number;
  }
) {
  const [bootstrap] = useState(() => {
    const nextSessionId = createSessionId();
    const persistedState = readPersistedStylistChatUiState(nextSessionId);
    return {
      sessionId: nextSessionId,
      profileContext: mergeProfileContext(
        persistedState?.profileContext ?? null,
        readStoredProfileContext(),
      ),
      persistedState: persistedState
        ? {
            ...persistedState,
            messages: getInitialVisibleMessages(persistedState.messages),
          }
        : null,
    };
  });
  const sessionId = bootstrap.sessionId;
  const bootstrapProfileContext = bootstrap.profileContext;
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
  const [visualizationOffer, setVisualizationOffer] = useState<VisualizationOfferState>(
    () =>
      persistedState?.visualizationOffer ??
      getLatestVisualizationOffer(persistedState?.messages ?? []) ??
      createEmptyVisualizationOffer()
  );
  const [lastUserActionType, setLastUserActionType] = useState<string | null>(
    () => persistedState?.lastUserActionType ?? null
  );
  const [lastVisualCtaShown, setLastVisualCtaShown] = useState<string | null>(
    () => persistedState?.lastVisualCtaShown ?? null
  );
  const [lastVisualCtaConfirmed, setLastVisualCtaConfirmed] = useState<string | null>(
    () => persistedState?.lastVisualCtaConfirmed ?? null
  );
  const [profileContext, setProfileContext] = useState<FrontendProfileContext>(
    () => bootstrapProfileContext,
  );
  const [isHistoryLoading, setIsHistoryLoading] = useState(messages.length === 0);
  const [isLoadingOlderHistory, setIsLoadingOlderHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const [nextHistoryCursor, setNextHistoryCursor] = useState<number | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isRefreshingQueue, setIsRefreshingQueue] = useState(false);
  const [isRuntimePolicyLoading, setIsRuntimePolicyLoading] = useState(true);
  const [backendState, setBackendState] = useState<BackendState>("connected");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [clockTick, setClockTick] = useState(() => Date.now());
  const [chatCooldown, setChatCooldown] = useState<ChatCooldownState | null>(null);
  const messagesRef = useRef(messages);
  const chatAvailability: ChatAvailability = backendState === "error" ? "offline" : "online";
  const queueRefreshAvailableAt = activeJob?.queue_refresh_available_at
    ? Date.parse(activeJob.queue_refresh_available_at)
    : null;
  const queueRefreshRemainingSeconds = getRemainingSeconds(queueRefreshAvailableAt, clockTick);
  const hasActiveGenerationJob = isGenerationJobActive(activeJob);
  const isGenerationQueued = isGenerationJobQueued(activeJob);
  const isEditorLocked = isSending || isUploading || isRuntimePolicyLoading;
  const canSubmitDraft = Boolean(input.trim() || uploadedAsset);
  const chatCooldownRemainingSeconds = getRemainingSeconds(chatCooldown?.endsAt ?? null, clockTick);
  const isChatCooldownActive = chatCooldownRemainingSeconds > 0;
  const isSendLocked = isEditorLocked || !canSubmitDraft || isChatCooldownActive;
  const isGenerationActionLocked =
    isRuntimePolicyLoading || isSending || isUploading || isRefreshingQueue || hasActiveGenerationJob;
  const canRequestVisualization =
    visualizationOffer.canOfferVisualization &&
    !scenarioContext.pendingClarification &&
    !isGenerationActionLocked &&
    !isChatCooldownActive;

  const armChatCooldown = (actionType: ChatCooldownActionType, cooldownSeconds: number, endsAt?: number | null) => {
    if (cooldownSeconds <= 0) {
      setChatCooldown(null);
      return;
    }
    const resolvedEndsAt = endsAt ?? Date.now() + cooldownSeconds * 1000;
    if (!Number.isFinite(resolvedEndsAt) || resolvedEndsAt <= Date.now()) {
      setChatCooldown(null);
      return;
    }
    setChatCooldown({
      actionType,
      endsAt: resolvedEndsAt,
      cooldownSeconds,
    });
  };

  const syncCooldownFromErrorDetail = (detail: Record<string, unknown> | null) => {
    if (!detail) {
      return false;
    }
    const actionType = resolveCooldownActionType(detail);
    if (!actionType) {
      return false;
    }
    const nextAllowedAt =
      typeof detail.next_allowed_at === "string" ? Date.parse(detail.next_allowed_at) : Number.NaN;
    const fallbackCooldownSeconds =
      actionType === "try_other_style"
        ? cooldownConfig.tryOtherStyleCooldownSeconds
        : cooldownConfig.messageCooldownSeconds;
    const cooldownSeconds =
      typeof detail.cooldown_seconds === "number" && Number.isFinite(detail.cooldown_seconds)
        ? detail.cooldown_seconds
        : fallbackCooldownSeconds;
    const endsAt = Number.isFinite(nextAllowedAt)
      ? nextAllowedAt
      : typeof detail.retry_after_seconds === "number"
        ? Date.now() + detail.retry_after_seconds * 1000
        : null;
    armChatCooldown(actionType, cooldownSeconds, endsAt);
    return true;
  };

  const syncCooldownFromRuntimePolicy = (policyState: ChatRuntimePolicyState) => {
    const cooldown = policyState.cooldown;
    if (cooldown.is_allowed || cooldown.retry_after_seconds <= 0) {
      setChatCooldown(null);
      return;
    }

    const nextAllowedAt =
      typeof cooldown.next_allowed_at === "string" ? Date.parse(cooldown.next_allowed_at) : Number.NaN;
    const endsAt = Number.isFinite(nextAllowedAt)
      ? nextAllowedAt
      : Date.now() + cooldown.retry_after_seconds * 1000;
    armChatCooldown(cooldown.action_type, cooldown.cooldown_seconds, endsAt);
  };

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
    if (chatCooldown && chatCooldownRemainingSeconds <= 0) {
      setChatCooldown(null);
    }
  }, [chatCooldown, chatCooldownRemainingSeconds]);

  useEffect(() => {
    let isMounted = true;

    const loadInitialState = async () => {
      try {
        const [historyPage, context, runtimePolicyState] = await Promise.all([
          chatGateway.getHistoryPage(sessionId, { limit: INITIAL_HISTORY_PAGE_SIZE }),
          sessionContextGateway.getContext(sessionId),
          chatGateway.getRuntimePolicyState(sessionId),
        ]);
        if (!isMounted) {
          return;
        }

        const mergedHistory = mergeHistoryIntoCurrent(messagesRef.current, historyPage.items as ThreadMessage[]);
        const latestJob = getLatestGenerationJob(mergedHistory);
        const latestOffer = context.visualizationOffer.canOfferVisualization
          ? context.visualizationOffer
          : getLatestVisualizationOffer(mergedHistory);

        setMessages(mergedHistory);
        setScenarioContext(context);
        setVisualizationOffer(latestOffer);
        setActiveJob(latestJob);
        setHasMoreHistory(historyPage.has_more);
        setNextHistoryCursor(historyPage.next_before_message_id ?? null);
        setBackendState("connected");
        setErrorMessage(null);
        setIsHistoryLoading(false);
        setIsRuntimePolicyLoading(false);
        syncCooldownFromRuntimePolicy(runtimePolicyState);

        if (latestOffer.canOfferVisualization) {
          setLastVisualCtaShown(latestOffer.visualizationType ?? latestOffer.ctaText ?? "cta");
        }

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
        setIsRuntimePolicyLoading(false);
      }
    };

    void loadInitialState();

    return () => {
      isMounted = false;
    };
  }, [sessionId, locale]);

  useEffect(() => {
    writeStoredProfileContext(profileContext);
  }, [profileContext]);

  useEffect(() => {
    writePersistedStylistChatUiState(sessionId, {
      messages,
      uploadedAsset,
      activeJob,
      visualizationOffer,
      lastUserActionType,
      lastVisualCtaShown,
      lastVisualCtaConfirmed,
      profileContext,
    });
  }, [
    sessionId,
    messages,
    uploadedAsset,
    activeJob,
    visualizationOffer,
    lastUserActionType,
    lastVisualCtaShown,
    lastVisualCtaConfirmed,
    profileContext,
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
        const nextJob = await generationGateway.getStatus(activeJob.public_id);
        if (isCancelled) {
          return;
        }
        const mergedJob = mergeQueuedJobState(activeJob, nextJob);
        setBackendState("connected");
        setErrorMessage(null);
        setActiveJob(mergedJob);
        setMessages((current) => syncGenerationJobInMessages(current, mergedJob));

        if (
          mergedJob.status === "completed" ||
          mergedJob.status === "failed" ||
          mergedJob.status === "cancelled"
        ) {
          const freshContext = await sessionContextGateway.getContext(sessionId);
          if (isCancelled) {
            return;
          }
          setScenarioContext(freshContext);
          setVisualizationOffer(freshContext.visualizationOffer);
        }
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
  }, [activeJob?.public_id, activeJob?.status, locale, sessionId]);

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
    setVisualizationOffer(response.visualizationOffer);
    setMessages((current) => [...current, response.assistantMessage]);
    setActiveJob(response.generationJob ?? previousActiveJob);
    if (response.visualizationOffer.canOfferVisualization) {
      setLastVisualCtaShown(response.visualizationOffer.visualizationType ?? response.visualizationOffer.ctaText);
    }
  };

  const runQuickAction = async (actionId: CommandName) => {
    if (isGenerationActionLocked || isChatCooldownActive) {
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
    setLastUserActionType("quick_action_style_exploration");

    try {
      const clientMessageId = createClientMessageId();
      const response = await runStyleExplorationCommand({
        sessionId,
        locale,
        clientMessageId,
        profileContext,
      });

      setUploadedAsset(null);
      armChatCooldown("try_other_style", cooldownConfig.tryOtherStyleCooldownSeconds);
      handleServerResponse({ response, previousActiveJob });
    } catch (error) {
      setBackendState("error");
      syncCooldownFromErrorDetail(getErrorPayloadDetail(error));
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
    const recentProfileUpdate =
      composerSource === "followup"
        ? extractProfileUpdateFromClarification({
            questionText: scenarioContext.pendingClarificationText,
            answerText: draftInput.trim(),
          })
        : null;
    const nextProfileContext = mergeProfileContext(profileContext, recentProfileUpdate);

    setMessages((current) => [...current, optimisticMessage]);
    setInput("");
    setUploadedAsset(null);
    setIsSending(true);
    setBackendState("connecting");
    setErrorMessage(null);
    setLastUserActionType(composerSource);

    try {
      const response =
        composerSource === "followup"
          ? await submitFollowupClarification({
              sessionId,
              locale,
              message: draftInput.trim() || null,
              assetId: draftUploadedAsset?.id ?? null,
              clientMessageId,
              profileContext: nextProfileContext,
              profileRecentUpdate: recentProfileUpdate,
            })
          : await sendFreeformMessage(
              buildFreeformMessagePayload({
                sessionId,
                locale,
                message: draftInput.trim() || null,
                assetId: draftUploadedAsset?.id ?? null,
                clientMessageId,
                profileContext: nextProfileContext,
                profileRecentUpdate: recentProfileUpdate,
              })
            );

      armChatCooldown("message", cooldownConfig.messageCooldownSeconds);
      setProfileContext(nextProfileContext);
      handleServerResponse({ response, previousActiveJob });
    } catch (error) {
      setMessages((current) => current.filter((message) => message.id !== optimisticMessage.id));
      setInput(draftInput);
      setUploadedAsset(draftUploadedAsset);
      setBackendState("error");
      syncCooldownFromErrorDetail(getErrorPayloadDetail(error));
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

  const requestVisualizationFromCta = async () => {
    if (!canRequestVisualization) {
      return;
    }

    const previousActiveJob = activeJob;
    setIsSending(true);
    setBackendState("connecting");
    setErrorMessage(null);
    setLastUserActionType("visualization_cta");

    try {
      const clientMessageId = createClientMessageId();
      const response = await requestVisualization({
        sessionId,
        locale,
        visualizationOffer,
        assetId: uploadedAsset?.id ?? null,
        clientMessageId,
        profileContext,
      });
      setLastVisualCtaConfirmed(
        visualizationOffer.visualizationType ?? visualizationOffer.ctaText ?? "visualization_cta"
      );
      setUploadedAsset(null);
      armChatCooldown("message", cooldownConfig.messageCooldownSeconds);
      handleServerResponse({ response, previousActiveJob });
    } catch (error) {
      setBackendState("error");
      syncCooldownFromErrorDetail(getErrorPayloadDetail(error));
      setErrorMessage(
        error instanceof Error && error.message
          ? error.message
          : locale === "ru"
            ? "Не удалось запросить визуализацию."
            : "Could not request the visualization."
      );
    } finally {
      setIsSending(false);
    }
  };

  const refreshGenerationStatus = async () => {
    if (!activeJob || activeJob.status !== "pending" || isRefreshingQueue) {
      return;
    }

    setIsRefreshingQueue(true);
    try {
      const nextJob =
        scenarioContext.activeMode === "style_exploration"
          ? await retryStyleExploration(activeJob.public_id)
          : await retryGeneration(activeJob.public_id);
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
    visualizationOffer,
    activeJob,
    isHistoryLoading,
    isLoadingOlderHistory,
    hasMoreHistory,
    isSending,
    isUploading,
    isEditorLocked,
    isSendLocked,
    isGenerationActionLocked,
    isChatCooldownActive,
    chatCooldownRemainingSeconds,
    chatCooldownActionType: chatCooldown?.actionType ?? null,
    chatCooldownSeconds: chatCooldown?.cooldownSeconds ?? 0,
    isRefreshingQueue,
    hasActiveGenerationJob,
    isGenerationQueued,
    queueRefreshRemainingSeconds,
    backendState,
    chatAvailability,
    errorMessage,
    canRequestVisualization,
    loadOlderHistory,
    runQuickAction,
    sendComposerMessage,
    handleAttachAsset,
    requestVisualization: requestVisualizationFromCta,
    refreshGenerationStatus,
  };
}
