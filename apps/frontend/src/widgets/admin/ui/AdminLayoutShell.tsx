"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { useI18n } from "@/shared/i18n/I18nProvider";
import { cn } from "@/shared/lib/cn";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SoftButton } from "@/shared/ui/SoftButton";

const links = [
  { href: "/admin", key: "dashboard", accent: "Overview" },
  { href: "/admin/projects", key: "projects", accent: "Portfolio" },
  { href: "/admin/posts", key: "posts", accent: "Editorial" },
  { href: "/admin/contacts", key: "contacts", accent: "Inbox" },
  { href: "/admin/chats", key: "chats", accent: "Audit" },
  { href: "/admin/jobs", key: "jobs", accent: "Queue" },
  { href: "/admin/parser", key: "parser", accent: "Ingestion" },
  { href: "/admin/settings", key: "settings", accent: "Runtime" }
] as const;

export function AdminLayoutShell({ children }: { children: React.ReactNode }) {
  const { isReady, isAuthenticated, logout } = useAdminAuth();
  const { t } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const isLoginPage = pathname === "/admin/login";

  useEffect(() => {
    if (!isReady || isLoginPage) {
      return;
    }
    if (!isAuthenticated) {
      router.replace("/admin/login");
    }
  }, [isAuthenticated, isLoginPage, isReady, router]);

  if (!isReady) {
    return (
      <div className="page-shell py-16">
        <div className="rounded-[var(--radius-panel)] border border-[var(--border-soft)] bg-white/75 p-6 text-sm text-[var(--text-secondary)] shadow-[var(--shadow-soft-sm)]">
          Loading admin workspace...
        </div>
      </div>
    );
  }

  if (isLoginPage) {
    return <div className="min-h-screen">{children}</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="page-shell grid min-h-screen gap-6 py-6 lg:grid-cols-[300px_1fr]">
      <aside className="sticky top-6 h-fit space-y-5 rounded-[32px] border border-white/75 bg-white/80 p-5 shadow-[var(--shadow-soft-xl)] backdrop-blur">
        <div className="rounded-[26px] border border-[var(--border-soft)] bg-[linear-gradient(135deg,var(--surface-ink),#25211d)] p-5 text-white shadow-[var(--shadow-soft-md)]">
          <div className="flex items-center justify-between gap-3">
            <p className="font-mono text-xs uppercase tracking-[0.28em] text-white/50">Admin</p>
            <PillBadge tone="neutral" size="sm" className="border-white/20 bg-white/10 text-white">
              Live
            </PillBadge>
          </div>
          <h2 className="mt-3 text-2xl font-semibold tracking-[-0.03em]">Control room</h2>
          <p className="mt-2 text-sm leading-6 text-white/60">
            Chats, jobs, content and runtime settings in one operational surface.
          </p>
        </div>
        <nav className="space-y-2.5">
          {links.map((link) => {
            const isActive = link.href === "/admin"
              ? pathname === link.href
              : pathname === link.href || pathname.startsWith(`${link.href}/`);
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "group flex items-center justify-between gap-3 rounded-[22px] border px-4 py-3 text-sm transition duration-200",
                  isActive
                    ? "border-[var(--surface-ink)] bg-[var(--surface-ink)] text-white shadow-[var(--shadow-soft-md)]"
                    : "border-[var(--border-soft)] bg-white/75 text-[var(--text-secondary)] hover:border-[var(--border-strong)] hover:bg-white hover:text-[var(--text-primary)]"
                )}
              >
                <span className="font-medium">{t(link.key)}</span>
                <span
                  className={cn(
                    "rounded-[var(--radius-pill)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em]",
                    isActive
                      ? "bg-white/10 text-white/70"
                      : "bg-[var(--surface-secondary)] text-[var(--text-muted)] group-hover:bg-[var(--surface-elevated)]"
                  )}
                >
                  {link.accent}
                </span>
              </Link>
            );
          })}
        </nav>
        <SoftButton
          tone="neutral"
          shape="surface"
          fullWidth
          onClick={() => {
            logout();
            router.replace("/admin/login");
          }}
        >
          {t("logout")}
        </SoftButton>
      </aside>
      <main className="min-w-0 space-y-6">{children}</main>
    </div>
  );
}
