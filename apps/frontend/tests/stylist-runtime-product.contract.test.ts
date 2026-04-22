import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import { buildChatCooldownSendControlState } from "@/features/chat-cooldown/model/cooldownSendControl";
import type { StylistRuntimeSettings } from "@/shared/api/types";
import {
  getInitialVisibleMessages,
  LOCAL_CHAT_RETENTION_DAYS,
  mergeHistoryIntoCurrent,
  prunePersistedStylistChatUiState,
} from "@/processes/stylist-chat/model/lib";
import type { ThreadMessage } from "@/entities/chat-message/model/types";
import type { GenerationJobState } from "@/entities/generation-job/model/types";
import type { UploadedAsset } from "@/shared/api/types";
import {
  buildStylistRuntimeSettingsUpdatePayload,
  toBoundedInteger,
} from "@/widgets/admin/model/stylistRuntimeSettings";

function readSource(relativePath: string) {
  return readFileSync(new URL(`../src/${relativePath}`, import.meta.url), "utf8");
}

function assertExplanationFollowsGeneratedImage(source: string) {
  const imageIndex = source.indexOf("<Image");
  const explanationIndex = source.indexOf("<GenerationStyleExplanation");

  assert.notEqual(imageIndex, -1);
  assert.notEqual(explanationIndex, -1);
  assert.ok(imageIndex < explanationIndex);
}

function buildSettings(overrides: Partial<StylistRuntimeSettings> = {}): StylistRuntimeSettings {
  return {
    id: 1,
    daily_generation_limit_non_admin: 7,
    daily_chat_seconds_limit_non_admin: 900,
    message_cooldown_seconds: 12,
    try_other_style_cooldown_seconds: 60,
    created_at: "2026-04-21T00:00:00Z",
    updated_at: "2026-04-21T00:00:00Z",
    ...overrides,
  };
}

function buildThreadMessage(overrides: Partial<ThreadMessage>): ThreadMessage {
  return {
    id: 1,
    session_id: "session-1",
    role: "assistant",
    locale: "ru",
    content: "message",
    generation_job_id: null,
    generation_job: null,
    uploaded_asset: null,
    payload: {},
    created_at: "2026-04-21T10:00:00.000Z",
    updated_at: "2026-04-21T10:00:00.000Z",
    ...overrides,
  };
}

function buildUploadedAsset(overrides: Partial<UploadedAsset>): UploadedAsset {
  return {
    id: 1,
    original_filename: "asset.png",
    storage_path: "uploads/asset.png",
    public_url: "/media/uploads/asset.png",
    mime_type: "image/png",
    size_bytes: 128,
    asset_type: "garment_photo",
    storage_backend: "local",
    created_at: "2026-04-21T10:00:00.000Z",
    updated_at: "2026-04-21T10:00:00.000Z",
    ...overrides,
  };
}

function buildGenerationJob(overrides: Partial<GenerationJobState>): GenerationJobState {
  return {
    id: 1,
    public_id: "job-1",
    session_id: "session-1",
    provider: "comfyui",
    status: "completed",
    input_text: null,
    prompt: "prompt",
    recommendation_ru: "",
    recommendation_en: "",
    input_asset: null,
    result_url: "/media/generated/result.png",
    external_job_id: null,
    progress: 100,
    provider_payload: {},
    operation_log: [],
    started_at: null,
    completed_at: null,
    deleted_at: null,
    created_at: "2026-04-21T10:00:00.000Z",
    updated_at: "2026-04-21T10:00:00.000Z",
    ...overrides,
  };
}

test("style explanation stays attached below generated images", () => {
  assertExplanationFollowsGeneratedImage(
    readSource("entities/generation-job/ui/GenerationResultSurface.tsx"),
  );
  assertExplanationFollowsGeneratedImage(
    readSource("entities/generation-job/ui/GenerationResultCard.tsx"),
  );
});

test("admin runtime settings saves every configurable non-admin limit and cooldown", () => {
  const payload = buildStylistRuntimeSettingsUpdatePayload(buildSettings());

  assert.deepEqual(payload, {
    daily_generation_limit_non_admin: 7,
    daily_chat_seconds_limit_non_admin: 900,
    message_cooldown_seconds: 12,
    try_other_style_cooldown_seconds: 60,
  });
  assert.equal(toBoundedInteger(3601, 12, 0, 3600), 3600);
  assert.equal(toBoundedInteger(-1, 12, 0, 3600), 0);
  assert.equal(toBoundedInteger("not-a-number", 12, 0, 3600), 12);
});

test("cooldown send control shows countdown progress and blocks submit while locked", () => {
  const locked = buildChatCooldownSendControlState({
    isLocked: true,
    secondsRemaining: 17,
    cooldownSeconds: 45,
  });

  assert.equal(locked.canSubmit, false);
  assert.equal(locked.ariaLabel, "Cooldown 17s");
  assert.equal(locked.clampedRemainingSeconds, 17);
  assert.equal(locked.progressRatio, 17 / 45);

  const disabled = buildChatCooldownSendControlState({
    isLocked: false,
    secondsRemaining: 0,
    disabled: true,
    disabledReason: "Message text is required",
  });

  assert.equal(disabled.canSubmit, false);
  assert.equal(disabled.ariaLabel, "Message text is required");
  assert.equal(disabled.title, "Message text is required");

  const unlocked = buildChatCooldownSendControlState({
    isLocked: false,
    secondsRemaining: 0,
  });

  assert.equal(unlocked.canSubmit, true);
  assert.equal(unlocked.ariaLabel, "Send message");
});

test("chat history merge does not append stale optimistic user messages after refresh", () => {
  const history = [
    buildThreadMessage({
      id: 101,
      role: "user",
      content: "Первое сообщение",
      created_at: "2026-04-21T10:00:00.000Z",
    }),
    buildThreadMessage({
      id: 102,
      role: "assistant",
      content: "Ответ",
      created_at: "2026-04-21T10:00:01.000Z",
    }),
  ];
  const staleOptimisticUser = buildThreadMessage({
    id: -1,
    role: "user",
    content: "Старое локальное сообщение",
    created_at: "2026-04-20T10:00:00.000Z",
    isOptimistic: true,
  });

  assert.deepEqual(mergeHistoryIntoCurrent([staleOptimisticUser], history), history);
  assert.deepEqual(getInitialVisibleMessages([staleOptimisticUser]), []);
});

test("chat history merge keeps fresh optimistic messages in chronological order", () => {
  const now = Date.now();
  const history = [
    buildThreadMessage({
      id: 201,
      role: "assistant",
      content: "Before",
      created_at: new Date(now - 30000).toISOString(),
    }),
    buildThreadMessage({
      id: 202,
      role: "assistant",
      content: "After",
      created_at: new Date(now - 5000).toISOString(),
    }),
  ];
  const freshOptimisticUser = buildThreadMessage({
    id: -2,
    role: "user",
    content: "Fresh pending",
    created_at: new Date(now - 15000).toISOString(),
    isOptimistic: true,
  });

  assert.deepEqual(
    mergeHistoryIntoCurrent([freshOptimisticUser], history).map((message) => message.content),
    ["Before", "Fresh pending", "After"],
  );
});

test("local chat retention prunes messages images and active jobs older than ten days", () => {
  const now = Date.parse("2026-04-22T12:00:00.000Z");
  const retainedAtBoundary = new Date(now - LOCAL_CHAT_RETENTION_DAYS * 24 * 60 * 60 * 1000).toISOString();
  const expiredBeforeBoundary = new Date(now - LOCAL_CHAT_RETENTION_DAYS * 24 * 60 * 60 * 1000 - 1000).toISOString();
  const retainedMessage = buildThreadMessage({ id: 301, content: "keep", created_at: retainedAtBoundary });
  const retainedMessageWithExpiredMedia = buildThreadMessage({
    id: 303,
    content: "keep text without stale media",
    created_at: retainedAtBoundary,
    generation_job_id: 99,
    generation_job: buildGenerationJob({ created_at: expiredBeforeBoundary }),
    uploaded_asset: buildUploadedAsset({ created_at: expiredBeforeBoundary }),
  });
  const expiredMessage = buildThreadMessage({ id: 302, content: "drop", created_at: expiredBeforeBoundary });

  const pruned = prunePersistedStylistChatUiState(
    {
      messages: [expiredMessage, retainedMessage, retainedMessageWithExpiredMedia],
      uploadedAsset: buildUploadedAsset({ created_at: expiredBeforeBoundary }),
      activeJob: buildGenerationJob({ created_at: expiredBeforeBoundary }),
      visualizationOffer: {
        canOfferVisualization: false,
        ctaText: null,
        visualizationType: null,
      },
      lastUserActionType: null,
      lastVisualCtaShown: null,
      lastVisualCtaConfirmed: null,
      presentationProfile: {},
    },
    now,
  );

  assert.deepEqual(pruned.messages.map((message) => message.content), ["keep", "keep text without stale media"]);
  assert.equal(pruned.messages[1]?.generation_job_id, null);
  assert.equal(pruned.messages[1]?.generation_job, null);
  assert.equal(pruned.messages[1]?.uploaded_asset, null);
  assert.equal(pruned.uploadedAsset, null);
  assert.equal(pruned.activeJob, null);
});

test("local chat history merge ignores backend messages beyond retention", () => {
  const now = Date.now();
  const expiredHistoryMessage = buildThreadMessage({
    id: 401,
    role: "assistant",
    content: "expired from backend",
    created_at: new Date(now - LOCAL_CHAT_RETENTION_DAYS * 24 * 60 * 60 * 1000 - 1000).toISOString(),
  });

  assert.deepEqual(mergeHistoryIntoCurrent([], [expiredHistoryMessage]), []);
});

test("rounded chat UI polish covers composer buttons bubbles chips and surfaces", () => {
  const panel = readSource("widgets/stylist-chat-panel/ui/StylistChatPanel.tsx");
  const composer = readSource("widgets/stylist-chat-panel/ui/ChatComposerDock.tsx");
  const quickActions = readSource("widgets/stylist-chat-panel/ui/ChatQuickActionsBar.tsx");
  const thread = readSource("widgets/chat-thread/ui/ChatThread.tsx");
  const inputSurface = readSource("shared/ui/InputSurface.tsx");
  const softButton = readSource("shared/ui/SoftButton.tsx");
  const generationSurface = readSource("entities/generation-job/ui/GenerationResultSurface.tsx");
  const generationStatusRail = readSource("features/chat/ui/GenerationStatusRail.tsx");

  assert.match(panel, /rounded-\[36px\]/);
  assert.match(composer, /rounded-\[32px\]/);
  assert.match(composer, /<InputSurface/);
  assert.match(quickActions, /<SoftButton/);
  assert.match(quickActions, /shape="pill"/);
  assert.match(quickActions, /shape="surface"/);
  assert.match(inputSurface, /rounded-\[var\(--radius-panel\)\]/);
  assert.match(softButton, /rounded-\[var\(--radius-pill\)\]/);
  assert.match(softButton, /rounded-\[var\(--radius-bubble\)\]/);
  assert.match(thread, /rounded-\[24px\]/);
  assert.match(generationSurface, /rounded-\[28px\]/);
  assert.match(generationStatusRail, /rounded-\[28px\]/);
});
