import assert from "node:assert/strict";
import test from "node:test";

import { adaptChatResponse } from "@/entities/chat-session/model/adapters";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
} from "@/features/run-chat-command/model/runChatCommand";
import { buildFollowupMessagePayload } from "@/features/send-chat-message/model/sendChatMessage";
import {
  createDefaultScenarioContext,
  getScenarioPlaceholder,
  shouldRenderPendingGeneration,
} from "@/processes/stylist-chat/model/lib";
import type { StylistMessageResponse } from "@/shared/api/types";

test("quick action builds a typed garment_matching command payload", () => {
  const action = getQuickActionDefinitions("ru").find((item) => item.id === "garment_matching");
  assert.ok(action);

  const payload = buildQuickActionCommandPayload({
    sessionId: "session-1",
    locale: "ru",
    action,
  });

  assert.equal(payload.requestedIntent, "garment_matching");
  assert.equal(payload.commandName, "garment_matching");
  assert.equal(payload.commandStep, "start");
  assert.equal(payload.message, null);
  assert.equal(payload.assetId, null);
});

test("follow-up payload keeps source metadata and does not override mode locally", () => {
  const payload = buildFollowupMessagePayload({
    sessionId: "session-2",
    locale: "ru",
    message: "Да, речь про тёмно-синий пиджак",
    assetId: null,
  });

  assert.equal(payload.metadata?.source, "followup");
  assert.equal(payload.requestedIntent, undefined);
});

test("garment command does not require asset to enter the mode", () => {
  const action = getQuickActionDefinitions("en").find((item) => item.id === "garment_matching");
  assert.ok(action);

  const payload = buildQuickActionCommandPayload({
    sessionId: "session-3",
    locale: "en",
    action,
    assetId: null,
  });

  assert.equal(payload.assetId, null);
  assert.equal(payload.requestedIntent, "garment_matching");
});

test("quick action builds a typed occasion_outfit command payload", () => {
  const action = getQuickActionDefinitions("en").find((item) => item.id === "occasion_outfit");
  assert.ok(action);

  const payload = buildQuickActionCommandPayload({
    sessionId: "session-occ-1",
    locale: "en",
    action,
  });

  assert.equal(payload.requestedIntent, "occasion_outfit");
  assert.equal(payload.commandName, "occasion_outfit");
  assert.equal(payload.commandStep, "start");
  assert.equal(payload.message, null);
});

test("garment flow placeholder shows an example-style hint after stage 4", () => {
  const context = createDefaultScenarioContext();
  context.activeMode = "garment_matching";

  const placeholder = getScenarioPlaceholder(context, "ru");

  assert.equal(placeholder, "Например: тёмно-синяя джинсовая рубашка oversize");
});

test("occasion flow placeholder shows an event-specific example after stage 5", () => {
  const context = createDefaultScenarioContext();
  context.activeMode = "occasion_outfit";

  const placeholder = getScenarioPlaceholder(context, "en");

  assert.equal(
    placeholder,
    "For example: an evening contemporary art exhibition in autumn, I want to look thoughtful and a little bold"
  );
});

test("text_and_generate response adapts to text plus pending image lifecycle", () => {
  const response: StylistMessageResponse = {
    session_id: "session-4",
    recommendation_text: "Here is the outfit direction.",
    prompt: "editorial flat lay",
    assistant_message: {
      id: 10,
      session_id: "session-4",
      role: "assistant",
      locale: "en",
      content: "Here is the outfit direction.",
      generation_job_id: 7,
      generation_job: null,
      uploaded_asset: null,
      payload: {},
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
    },
    generation_job: {
      id: 7,
      public_id: "job-1",
      session_id: "session-4",
      provider: "mock",
      status: "pending",
      input_text: null,
      prompt: "editorial flat lay",
      recommendation_ru: "",
      recommendation_en: "Here is the outfit direction.",
      input_asset: null,
      result_url: null,
      external_job_id: null,
      progress: 0,
      body_height_cm: null,
      body_weight_kg: null,
      error_message: null,
      provider_payload: {},
      operation_log: [],
      started_at: null,
      completed_at: null,
      deleted_at: null,
      queue_position: 1,
      queue_ahead: 0,
      queue_total: 1,
      queue_refresh_available_at: null,
      queue_refresh_retry_after_seconds: null,
      created_at: "2026-04-09T00:00:00Z",
      updated_at: "2026-04-09T00:00:00Z",
    },
    timestamp: "2026-04-09T00:00:00Z",
    decision: {
      decision_type: "text_and_generate",
      active_mode: "style_exploration",
      flow_state: "generation_queued",
      text_reply: "Here is the outfit direction.",
      generation_payload: {
        prompt: "editorial flat lay",
        image_brief_en: "editorial outfit",
        recommendation_text: "Here is the outfit direction.",
        input_asset_id: null,
        generation_intent: {
          mode: "style_exploration",
          trigger: "style_exploration",
          reason: "new_style_direction_selected",
          must_generate: true,
          job_priority: "normal",
          source_message_id: 9,
        },
      },
      job_id: "job-1",
      context_patch: {},
      error_code: null,
    },
    session_context: {
      version: 1,
      active_mode: "style_exploration",
      requested_intent: "style_exploration",
      flow_state: "generation_queued",
      pending_clarification: null,
      clarification_kind: null,
      clarification_attempts: 0,
      should_auto_generate: true,
      anchor_garment: null,
      occasion_context: null,
      style_history: [],
      last_generation_prompt: "editorial flat lay",
      last_generated_outfit_summary: "Here is the outfit direction.",
      conversation_memory: [],
      command_context: {
        command_name: "style_exploration",
        command_step: "start",
        metadata: { source: "quick_action" },
      },
      current_style_id: "soft-retro-prep",
      current_style_name: "Soft Retro Prep",
      current_job_id: "job-1",
      last_decision_type: "text_and_generate",
      generation_intent: {
        mode: "style_exploration",
        trigger: "style_exploration",
        reason: "new_style_direction_selected",
        must_generate: true,
        job_priority: "normal",
        source_message_id: 9,
      },
      updated_at: "2026-04-09T00:00:00Z",
      updated_by_message_id: 9,
    },
  };

  const adapted = adaptChatResponse(response);

  assert.equal(adapted.decisionType, "text_and_generate");
  assert.equal(adapted.replyText, "Here is the outfit direction.");
  assert.equal(adapted.jobId, "job-1");
  assert.equal(adapted.generationJob?.public_id, "job-1");
  assert.equal(shouldRenderPendingGeneration(adapted), true);
});
