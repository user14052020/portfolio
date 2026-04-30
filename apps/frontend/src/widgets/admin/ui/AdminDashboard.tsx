"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getBlogPosts, getContactRequests, getGenerationJobs, getProjects } from "@/shared/api/browser-client";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

type DashboardStats = {
  projects: number;
  posts: number;
  contacts: number;
  jobs: number;
};

type DashboardStatus = "idle" | "loading" | "ready" | "error";

const DASHBOARD_CARDS: Array<{
  key: keyof DashboardStats;
  label: string;
  description: string;
  tone: "accent" | "mint" | "lilac" | "warning";
}> = [
  {
    key: "projects",
    label: "Projects",
    description: "Portfolio entries available to the public surface.",
    tone: "accent",
  },
  {
    key: "posts",
    label: "Posts",
    description: "Writing and content records in the CMS.",
    tone: "lilac",
  },
  {
    key: "contacts",
    label: "Contacts",
    description: "Inbound messages waiting in the inbox.",
    tone: "mint",
  },
  {
    key: "jobs",
    label: "Generation jobs",
    description: "Visual generation records tracked by the admin audit layer.",
    tone: "warning",
  },
];

export function AdminDashboard() {
  const { tokens } = useAdminAuth();
  const [stats, setStats] = useState<DashboardStats>({
    projects: 0,
    posts: 0,
    contacts: 0,
    jobs: 0,
  });
  const [status, setStatus] = useState<DashboardStatus>("idle");

  useEffect(() => {
    if (!tokens?.access_token) {
      setStatus("idle");
      return;
    }

    let cancelled = false;
    setStatus("loading");

    Promise.all([
      getProjects({ includeDrafts: true }, tokens.access_token),
      getBlogPosts({ includeDrafts: true }, tokens.access_token),
      getContactRequests(tokens.access_token),
      getGenerationJobs(tokens.access_token),
    ])
      .then(([projects, posts, contacts, jobs]) => {
        if (cancelled) {
          return;
        }
        setStats({
          projects: projects.length,
          posts: posts.length,
          contacts: contacts.length,
          jobs: jobs.length,
        });
        setStatus("ready");
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        setStats({
          projects: 0,
          posts: 0,
          contacts: 0,
          jobs: 0,
        });
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [tokens?.access_token]);

  return (
    <div className="space-y-6">
      <SurfaceCard
        variant="tinted"
        header={
          <SectionHeader
            eyebrow="Admin control room"
            title="Operational overview"
            description="A compact pulse check for content, requests, and generation activity across the portfolio runtime."
            action={
              <PillBadge tone={status === "error" ? "rose" : status === "loading" ? "warning" : "success"}>
                {status === "idle" ? "auth required" : status}
              </PillBadge>
            }
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {DASHBOARD_CARDS.map((card) => (
            <DashboardStatCard
              key={card.key}
              label={card.label}
              description={card.description}
              value={stats[card.key]}
              tone={card.tone}
              isLoading={status === "loading"}
            />
          ))}
        </div>

        {status === "error" ? (
          <div className="mt-5 rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            Failed to load dashboard metrics. Check admin authorization and backend availability.
          </div>
        ) : null}
      </SurfaceCard>
    </div>
  );
}

function DashboardStatCard({
  label,
  description,
  value,
  tone,
  isLoading,
}: {
  label: string;
  description: string;
  value: number;
  tone: "accent" | "mint" | "lilac" | "warning";
  isLoading: boolean;
}) {
  return (
    <div className="rounded-[28px] border border-[var(--border-soft)] bg-white/75 p-5 shadow-[var(--shadow-soft-sm)]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-[var(--text-primary)]">{label}</p>
          <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">{description}</p>
        </div>
        <PillBadge tone={tone} size="sm">
          total
        </PillBadge>
      </div>
      <p className="mt-6 font-display text-5xl leading-none text-[var(--text-primary)]">
        {isLoading ? "..." : value}
      </p>
    </div>
  );
}
