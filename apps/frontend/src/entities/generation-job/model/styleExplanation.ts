import type { GenerationJob } from "@/shared/api/types";

export function buildGenerationStyleExplanationLines(job: GenerationJob | null) {
  const explanation = job?.style_explanation;
  if (!explanation) {
    return [];
  }

  const lines: string[] = [];
  if (typeof explanation.short_explanation === "string" && explanation.short_explanation.trim()) {
    lines.push(explanation.short_explanation.trim());
  }
  if (
    typeof explanation.supporting_text === "string" &&
    explanation.supporting_text.trim() &&
    !lines.includes(explanation.supporting_text.trim())
  ) {
    lines.push(explanation.supporting_text.trim());
  }
  for (const item of explanation.distinct_points ?? []) {
    const cleaned = typeof item === "string" ? item.trim() : "";
    if (cleaned && !lines.includes(cleaned)) {
      lines.push(cleaned);
    }
    if (lines.length >= 4) {
      break;
    }
  }
  return lines.slice(0, 4);
}
