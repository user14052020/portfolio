import Link from "next/link";

import type { SiteSettings } from "@/shared/api/types";

export function Footer({ settings }: { settings: SiteSettings }) {
  return (
    <footer className="border-t border-white/60 pb-10 pt-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-800">{settings.brand_name}</p>
          <p className="text-sm text-slate-500">{settings.contact_email}</p>
        </div>
        <div className="flex flex-wrap gap-4">
          {Object.entries(settings.socials).map(([key, value]) => (
            <Link key={key} href={value} className="text-sm text-slate-600 transition hover:text-slate-900">
              {key}
            </Link>
          ))}
        </div>
      </div>
    </footer>
  );
}

