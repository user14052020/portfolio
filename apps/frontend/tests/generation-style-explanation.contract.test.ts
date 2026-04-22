import assert from "node:assert/strict";
import test from "node:test";

import { buildGenerationStyleExplanationLines } from "@/entities/generation-job/model/styleExplanation";
import type { GenerationJob } from "@/shared/api/types";

function buildJob(styleExplanation: GenerationJob["style_explanation"]): GenerationJob {
  return {
    id: 1,
    public_id: "job-style-explanation-1",
    session_id: "session-style-explanation-1",
    provider: "mock",
    status: "completed",
    input_text: null,
    prompt: "soft prep editorial flat lay",
    recommendation_ru: "",
    recommendation_en: "Try a softer prep direction.",
    input_asset: null,
    result_url: "/generated/soft-prep.png",
    external_job_id: null,
    progress: 100,
    body_height_cm: null,
    body_weight_kg: null,
    error_message: null,
    provider_payload: {},
    operation_log: [],
    started_at: null,
    completed_at: "2026-04-21T00:00:00Z",
    deleted_at: null,
    queue_position: null,
    queue_ahead: null,
    queue_total: null,
    queue_refresh_available_at: null,
    queue_refresh_retry_after_seconds: null,
    style_explanation: styleExplanation,
    created_at: "2026-04-21T00:00:00Z",
    updated_at: "2026-04-21T00:00:00Z",
  };
}

test("generation style explanation renders persisted explanation text", () => {
  const lines = buildGenerationStyleExplanationLines(
    buildJob({
      style_id: "soft-retro-prep",
      style_name: "Soft Retro Prep",
      short_explanation: "  Soft Retro Prep warms up collegiate dressing. ",
      supporting_text: "It keeps prep recognizable but softer.",
      distinct_points: ["Warm prep palette", "Warm prep palette", "Relaxed polish"],
    }),
  );

  assert.deepEqual(lines, [
    "Soft Retro Prep warms up collegiate dressing.",
    "It keeps prep recognizable but softer.",
    "Warm prep palette",
    "Relaxed polish",
  ]);
});

test("generation style explanation omits empty and duplicate text", () => {
  const lines = buildGenerationStyleExplanationLines(
    buildJob({
      style_id: "soft-retro-prep",
      style_name: "Soft Retro Prep",
      short_explanation: "Soft Retro Prep warms up collegiate dressing.",
      supporting_text: "Soft Retro Prep warms up collegiate dressing.",
      distinct_points: ["", "  Soft Retro Prep warms up collegiate dressing.  ", "Gentle structure"],
    }),
  );

  assert.deepEqual(lines, [
    "Soft Retro Prep warms up collegiate dressing.",
    "Gentle structure",
  ]);
});

test("generation style explanation renders nothing when metadata is absent", () => {
  assert.deepEqual(buildGenerationStyleExplanationLines(buildJob(null)), []);
});
