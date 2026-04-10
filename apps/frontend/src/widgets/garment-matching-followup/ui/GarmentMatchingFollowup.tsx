import type { Locale } from "@/shared/api/types";

export function GarmentMatchingFollowup({
  locale,
  pendingClarificationText,
}: {
  locale: Locale;
  pendingClarificationText: string | null;
}) {
  if (!pendingClarificationText) {
    return null;
  }

  return (
    <div className="border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
      <p className="font-medium">
        {locale === "ru" ? "Активный сценарий" : "Active scenario"}: garment_matching
      </p>
      <p className="mt-1 leading-6">{pendingClarificationText}</p>
    </div>
  );
}
