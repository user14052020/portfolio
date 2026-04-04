"use client";

import Link from "next/link";
import { Button } from "@mantine/core";

import { useI18n } from "@/shared/i18n/I18nProvider";
import { LanguageSwitcher } from "@/shared/ui/LanguageSwitcher";

export function Header({
  email,
  onOpenContact
}: {
  email: string;
  onOpenContact: () => void;
}) {
  const { locale, t } = useI18n();

  return (
    <header className="sticky top-0 z-40 mx-auto grid w-full max-w-7xl items-center gap-3 border border-slate-200 bg-white px-5 py-3 lg:grid-cols-[1fr_auto_1fr] lg:gap-4">
      <div className="hidden items-center lg:flex">
        <Link href={`mailto:${email}`} className="text-sm text-slate-600">
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
        <Button radius="xl" variant="light" onClick={onOpenContact}>
          {t("writeMe")}
        </Button>
      </div>
    </header>
  );
}
