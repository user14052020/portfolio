import type { Locale } from "@/shared/api/types";

export function ChatClarificationPanel({
  locale,
  text,
}: {
  locale: Locale;
  text: string;
}) {
  return (
    <div className="rounded-[28px] border border-amber-200/80 bg-amber-50/86 px-4 py-3 text-sm text-amber-900 shadow-[var(--shadow-soft-sm)]">
      <p className="font-semibold">{locale === "ru" ? "Нужно уточнение" : "Need a follow-up"}</p>
      <p className="mt-1 leading-6">{text}</p>
    </div>
  );
}
