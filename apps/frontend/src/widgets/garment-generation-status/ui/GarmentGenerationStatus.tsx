import type { GenerationJob } from "@/shared/api/types";
import { GenerationStatusPanel } from "@/widgets/generation-status/ui/GenerationStatusPanel";

export function GarmentGenerationStatus({
  job,
  locale,
  isRefreshing,
  queueRefreshRemainingSeconds,
  onRefresh,
}: {
  job: GenerationJob | null;
  locale: "ru" | "en";
  isRefreshing: boolean;
  queueRefreshRemainingSeconds: number;
  onRefresh: () => void;
}) {
  return (
    <GenerationStatusPanel
      job={job}
      locale={locale}
      isRefreshing={isRefreshing}
      queueRefreshRemainingSeconds={queueRefreshRemainingSeconds}
      onRefresh={onRefresh}
    />
  );
}
