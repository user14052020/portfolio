import type { Locale } from "@/shared/api/types";

export function ChatAttachedAssetChip({
  locale,
  filename,
  onRemove,
}: {
  locale: Locale;
  filename: string;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[28px] border border-[var(--border-soft)] bg-white/82 px-4 py-3 text-sm text-[var(--text-secondary)] shadow-[var(--shadow-soft-sm)]">
      <span className="min-w-0 truncate">
        {locale === "ru" ? "Прикреплённый asset" : "Attached asset"}: {filename}
      </span>
      <button
        type="button"
        onClick={onRemove}
        className="shrink-0 text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
      >
        {locale === "ru" ? "убрать" : "remove"}
      </button>
    </div>
  );
}
