"use client";

import Link from "next/link";

import { useI18n } from "@/shared/i18n/I18nProvider";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";
import { SoftButton } from "@/shared/ui/SoftButton";

export function Header({
  email,
  onOpenContact
}: {
  email: string;
  onOpenContact: () => void;
}) {
  const { t } = useI18n();

  return (
    <header className="sticky top-4 z-40 mx-auto grid w-full items-center gap-3 rounded-[var(--radius-pill)] border border-white/70 bg-white/80 px-4 py-3 shadow-[var(--shadow-soft-md)] backdrop-blur-xl lg:grid-cols-[1fr_auto_1fr] lg:gap-4 lg:px-5">
      <div className="hidden items-center lg:flex">
        <Link href={`mailto:${email}`} className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
          {email}
        </Link>
      </div>
      <div className="font-g8-display flex cursor-default select-none flex-wrap items-center justify-center gap-x-3 gap-y-1 text-center text-[13px] tracking-[0.01em] sm:text-sm md:gap-x-4 lg:gap-x-5">
        <span className="text-rose-500">{t("navProgramming")}</span>
        <span className="text-sky-500">{t("nav3D")}</span>
        <span className="text-emerald-500">{t("navMotion")}</span>
      </div>
      <div className="flex items-center justify-center gap-3 lg:justify-end">
        <LanguageSwitcher />
        <SoftButton tone="dark" shape="compact" onClick={onOpenContact}>
          {t("writeMe")}
        </SoftButton>
      </div>
    </header>
  );
}
