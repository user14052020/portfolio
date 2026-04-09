"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@mantine/core";
import { useEffect } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { useI18n } from "@/shared/i18n/I18nProvider";

const links = [
  { href: "/admin", key: "dashboard" },
  { href: "/admin/projects", key: "projects" },
  { href: "/admin/posts", key: "posts" },
  { href: "/admin/contacts", key: "contacts" },
  { href: "/admin/jobs", key: "jobs" },
  { href: "/admin/parser", key: "parser" },
  { href: "/admin/settings", key: "settings" }
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
    return <div className="page-shell py-16 text-sm text-slate-500">Loading admin workspace...</div>;
  }

  if (isLoginPage) {
    return <div className="min-h-screen">{children}</div>;
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="page-shell grid min-h-screen gap-6 py-6 lg:grid-cols-[280px_1fr]">
      <aside className="space-y-4 rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-glass">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.28em] text-slate-500">Admin</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-900">Control room</h2>
        </div>
        <nav className="space-y-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`block rounded-2xl px-4 py-3 text-sm transition ${
                pathname === link.href ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {t(link.key)}
            </Link>
          ))}
        </nav>
        <Button
          radius="xl"
          variant="light"
          fullWidth
          onClick={() => {
            logout();
            router.replace("/admin/login");
          }}
        >
          {t("logout")}
        </Button>
      </aside>
      <main className="space-y-6">{children}</main>
    </div>
  );
}
