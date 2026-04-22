"use client";

import { GenerationStatusRail } from "@/features/chat/ui/GenerationStatusRail";
import type { GenerationJob, Locale } from "@/shared/api/types";

function isGenerationProgressVisible(job: GenerationJob | null, isPreparing: boolean) {
  if (isPreparing && !job) {
    return true;
  }

  return job?.status === "pending" || job?.status === "queued" || job?.status === "running";
}

export function ChatGenerationDock({
  job,
  locale,
  isPreparing,
}: {
  job: GenerationJob | null;
  locale: Locale;
  isPreparing: boolean;
}) {
  if (!isGenerationProgressVisible(job, isPreparing)) {
    return null;
  }

  return (
    <div className="mb-3 rounded-[28px] border border-[var(--border-soft)] bg-white/70 p-2 shadow-[var(--shadow-soft-sm)]">
      <GenerationStatusRail job={job} locale={locale} isPreparing={isPreparing} />
    </div>
  );
}
