import type { GenerationJob } from "@/shared/api/types";
import { GenerationStatusPanel } from "@/widgets/generation-status/ui/GenerationStatusPanel";

export function StyleGenerationStatus({
  job,
  locale,
  currentStyleName,
  styleHistorySize,
  isRefreshing,
  queueRefreshRemainingSeconds,
  onRefresh,
}: {
  job: GenerationJob | null;
  locale: "ru" | "en";
  currentStyleName?: string | null;
  styleHistorySize?: number;
  isRefreshing: boolean;
  queueRefreshRemainingSeconds: number;
  onRefresh: () => void;
}) {
  return (
    <div className="space-y-2">
      {currentStyleName ? (
        <div className="border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
          {locale === "ru" ? "Текущее направление" : "Current direction"}: {currentStyleName}
          {styleHistorySize ? (
            <span className="ml-2 text-slate-500">
              {locale === "ru"
                ? `история: ${styleHistorySize}`
                : `history: ${styleHistorySize}`}
            </span>
          ) : null}
        </div>
      ) : null}
      <GenerationStatusPanel
        job={job}
        locale={locale}
        isRefreshing={isRefreshing}
        queueRefreshRemainingSeconds={queueRefreshRemainingSeconds}
        onRefresh={onRefresh}
      />
    </div>
  );
}
