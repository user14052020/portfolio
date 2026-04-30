import assert from "node:assert/strict";
import test from "node:test";

import { adaptChatResponse } from "@/entities/chat-session/model/adapters";
import {
  buildProfileClarificationSuggestions,
  buildProfileRequestEnvelope,
  extractProfileUpdateFromClarification,
  mergeProfileContext,
  normalizeProfileContext,
} from "@/entities/profile/model/profileContext";
import {
  buildQuickActionCommandPayload,
  getQuickActionDefinitions,
} from "@/features/run-chat-command/model/runChatCommand";
import { buildFollowupMessagePayload } from "@/features/send-chat-message/model/sendChatMessage";
import {
  createDefaultScenarioContext,
  getComposerMessageSource,
  shouldRenderPendingGeneration,
} from "@/processes/stylist-chat/model/lib";
import type { StylistMessageResponse } from "@/shared/api/types";

test("quick actions keep only style_exploration after stage 1", () => {
  const actions = getQuickActionDefinitions("ru");

  assert.equal(actions.length, 1);
  assert.equal(actions[0]?.id, "style_exploration");
});

test("style quick action builds a typed payload without asset coupling", () => {
  const action = getQuickActionDefinitions("en")[0];

  const payload = buildQuickActionCommandPayload({
    sessionId: "session-style-1",
    locale: "en",
    action,
    assetId: "asset-88",
    profileContext: {
      presentation_profile: "androgynous",
    },
  });

  assert.equal(payload.requestedIntent, "style_exploration");
  assert.equal(payload.commandName, "style_exploration");
  assert.equal(payload.commandStep, "start");
  assert.equal(payload.message, null);
  assert.equal(payload.assetId, null);
  assert.deepEqual(payload.profileContext, {
    presentation_profile: "androgynous",
  });
  assert.deepEqual(payload.metadata?.session_profile_context, {
    presentation_profile: "androgynous",
  });
});

test("follow-up payload keeps source metadata and does not override mode locally", () => {
  const payload = buildFollowupMessagePayload({
    sessionId: "session-2",
    locale: "ru",
    message: "Да, давай уточним детали",
    assetId: null,
  });

  assert.equal(payload.metadata?.source, "followup");
  assert.equal(payload.requestedIntent, undefined);
});

test("profile envelope ships normalized session profile and recent updates together", () => {
  const envelope = buildProfileRequestEnvelope({
    profileContext: {
      presentation_profile: "androgynous",
      comfort_preferences: ["balanced"],
    },
    recentUpdate: {
      fit_preferences: ["relaxed"],
    },
  });

  assert.deepEqual(envelope.profileContext, {
    presentation_profile: "androgynous",
    fit_preferences: ["relaxed"],
    comfort_preferences: ["balanced"],
  });
  assert.deepEqual(envelope.metadata.session_profile_context, envelope.profileContext);
  assert.deepEqual(envelope.metadata.profile_recent_updates, {
    fit_preferences: ["relaxed"],
  });
});

test("profile normalization preserves future extension fields", () => {
  const normalized = normalizeProfileContext({
    presentation_profile: "androgynous",
    height_cm: 176,
    wardrobe_constraints: {
      avoid_micro_bags: true,
    },
  });

  assert.deepEqual(normalized, {
    presentation_profile: "androgynous",
    height_cm: 176,
    wardrobe_constraints: {
      avoid_micro_bags: true,
    },
  });
});

test("profile envelope keeps extension-only profile fields", () => {
  const envelope = buildProfileRequestEnvelope({
    profileContext: {
      height_cm: 176,
    },
    recentUpdate: {
      wardrobe_constraints: {
        avoid_micro_bags: true,
      },
    },
  });

  assert.deepEqual(envelope.profileContext, {
    height_cm: 176,
    wardrobe_constraints: {
      avoid_micro_bags: true,
    },
  });
  assert.deepEqual(envelope.metadata.session_profile_context, envelope.profileContext);
  assert.deepEqual(envelope.metadata.profile_recent_updates, {
    wardrobe_constraints: {
      avoid_micro_bags: true,
    },
  });
});

test("profile clarification extraction recognizes silhouette follow-ups", () => {
  const update = extractProfileUpdateFromClarification({
    questionText: "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
    answerText: "Oversized please",
  });

  assert.deepEqual(update, {
    fit_preferences: ["oversized"],
  });
});

test("profile clarification extraction recognizes universal presentation replies", () => {
  const update = extractProfileUpdateFromClarification({
    questionText:
      "Which presentation direction should guide this look: feminine, masculine, androgynous, or universal?",
    answerText: "Universal please",
  });

  assert.deepEqual(update, {
    presentation_profile: "unisex",
  });
});

test("profile clarification suggestions expose quick picks for profile questions", () => {
  const suggestions = buildProfileClarificationSuggestions(
    "en",
    "Do you prefer a relaxed, fitted, or oversized silhouette for this look?",
  );

  assert.deepEqual(
    suggestions.map((suggestion) => suggestion.label),
    ["Relaxed", "Fitted", "Oversized"],
  );
});

test("presentation clarification suggestions align with universal wording", () => {
  const suggestions = buildProfileClarificationSuggestions(
    "en",
    "Which presentation direction should guide this look: feminine, masculine, androgynous, or universal?",
  );

  assert.deepEqual(
    suggestions.map((suggestion) => suggestion.label),
    ["Feminine", "Masculine", "Androgynous", "Universal"],
  );
});

test("profile context merge keeps normalized persistent preferences", () => {
  const merged = mergeProfileContext(
    normalizeProfileContext({
      presentation_profile: "feminine",
      preferred_items: ["Blazer", "Blazer"],
    }),
    {
      formality_preferences: ["smart casual"],
      color_preferences: ["Navy", "navy"],
    },
  );

  assert.deepEqual(merged, {
    presentation_profile: "feminine",
    formality_preferences: ["smart_casual"],
    color_preferences: ["navy"],
    preferred_items: ["blazer"],
  });
});

test("composer uses follow-up mode only while a clarification is pending", () => {
  const context = createDefaultScenarioContext();
  context.pendingClarification = false;

  assert.equal(getComposerMessageSource(context), "chat_input");

  context.pendingClarification = true;
  assert.equal(getComposerMessageSource(context), "followup");
});

test("text response adapts CTA fields for visualization offer", () => {
  const response: StylistMessageResponse = {
    session_id: "session-cta-1",
    recommendation_text: "Для выставки я бы собрал вытянутый образ с мягким верхом.",
    prompt: "",
    assistant_message: {
      id: 10,
      session_id: "session-cta-1",
      role: "assistant",
      locale: "ru",
      content: "Для выставки я бы собрал вытянутый образ с мягким верхом.",
      generation_job_id: null,
      generation_job: null,
      uploaded_asset: null,
      payload: {
        can_offer_visualization: true,
        cta_text: "Собрать flat lay референс?",
        visualization_type: "flat_lay_reference",
      },
      created_at: "2026-04-12T00:00:00Z",
      updated_at: "2026-04-12T00:00:00Z",
    },
    generation_job: null,
    timestamp: "2026-04-12T00:00:00Z",
    decision: {
      decision_type: "text_only",
      active_mode: "general_advice",
      flow_state: "ready_for_generation",
      text_reply: "Для выставки я бы собрал вытянутый образ с мягким верхом.",
      generation_payload: null,
      job_id: null,
      context_patch: {},
      telemetry: {},
      error_code: null,
      visualization_offer: {
        can_offer_visualization: true,
        cta_text: "Собрать flat lay референс?",
        visualization_type: "flat_lay_reference",
      },
      can_offer_visualization: true,
      cta_text: "Собрать flat lay референс?",
      visualization_type: "flat_lay_reference",
    },
    session_context: {
      version: 1,
      active_mode: "general_advice",
      requested_intent: null,
      flow_state: "ready_for_generation",
      pending_clarification: null,
      clarification_kind: null,
      clarification_attempts: 0,
      should_auto_generate: false,
      anchor_garment: null,
      occasion_context: null,
      style_history: [],
      last_generation_prompt: null,
      last_generated_outfit_summary: "Для выставки я бы собрал вытянутый образ с мягким верхом.",
      conversation_memory: [],
      command_context: null,
      current_style_id: null,
      current_style_name: null,
      current_job_id: null,
      last_generation_request_key: null,
      last_decision_type: "text_only",
      generation_intent: null,
      visualization_offer: {
        can_offer_visualization: true,
        cta_text: "Собрать flat lay референс?",
        visualization_type: "flat_lay_reference",
      },
      updated_at: "2026-04-12T00:00:00Z",
      updated_by_message_id: 10,
    },
  };

  const adapted = adaptChatResponse(response);

  assert.equal(adapted.decisionType, "text_only");
  assert.equal(adapted.visualizationOffer.canOfferVisualization, true);
  assert.equal(adapted.visualizationOffer.ctaText, "Собрать flat lay референс?");
  assert.equal(adapted.visualizationOffer.visualizationType, "flat_lay_reference");
});

test("text_and_generate response still renders pending generation", () => {
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
        metadata: {},
        generation_intent: {
          mode: "style_exploration",
          trigger: "style_exploration",
          reason: "style_exploration_quick_action",
          must_generate: true,
          job_priority: "normal",
          source_message_id: 9,
        },
      },
      job_id: "job-1",
      context_patch: {},
      telemetry: {},
      error_code: null,
      visualization_offer: null,
      can_offer_visualization: false,
      cta_text: null,
      visualization_type: null,
    },
    session_context: {
      version: 1,
      active_mode: "style_exploration",
      requested_intent: "style_exploration",
      flow_state: "generation_queued",
      pending_clarification: null,
      clarification_kind: null,
      clarification_attempts: 0,
      should_auto_generate: false,
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
      last_generation_request_key: null,
      last_decision_type: "text_and_generate",
      generation_intent: {
        mode: "style_exploration",
        trigger: "style_exploration",
        reason: "style_exploration_quick_action",
        must_generate: true,
        job_priority: "normal",
        source_message_id: 9,
      },
      visualization_offer: null,
      updated_at: "2026-04-09T00:00:00Z",
      updated_by_message_id: 9,
    },
  };

  const adapted = adaptChatResponse(response);

  assert.equal(adapted.decisionType, "text_and_generate");
  assert.equal(shouldRenderPendingGeneration(adapted), true);
});
