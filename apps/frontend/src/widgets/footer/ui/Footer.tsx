import Link from "next/link";

import type { SiteSettings } from "@/shared/api/types";

export function Footer({ settings }: { settings: SiteSettings }) {
  return (
    <footer className="pb-10 pt-2">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 rounded-[32px] border border-white/70 bg-white/60 px-5 py-5 shadow-[var(--shadow-soft-sm)] backdrop-blur md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">{settings.brand_name}</p>
          <p className="text-sm text-[var(--text-muted)]">{settings.contact_email}</p>
        </div>
        <div className="flex flex-wrap gap-4">
          {Object.entries(settings.socials).map(([key, value]) => (
            <Link key={key} href={value} className="text-sm text-[var(--text-secondary)] transition hover:text-[var(--text-primary)]">
              {key}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}
