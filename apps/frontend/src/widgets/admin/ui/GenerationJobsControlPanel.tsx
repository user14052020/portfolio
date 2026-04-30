"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { cancelGenerationJob, deleteGenerationJob, getGenerationJobs } from "@/shared/api/browser-client";
import type { GenerationJob } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

function isActive(job: GenerationJob) {
  return job.status === "pending" || job.status === "queued" || job.status === "running";
}

function getRecentOperations(job: GenerationJob) {
  return job.operation_log.slice(-3).reverse();
}

function getLastOperation(job: GenerationJob) {
  return job.operation_log[job.operation_log.length - 1] ?? null;
}

function statusTone(status: GenerationJob["status"]): "success" | "warning" | "rose" | "neutral" {
  if (status === "completed") {
    return "success";
  }
  if (status === "failed" || status === "cancelled") {
    return "rose";
  }
  if (status === "pending" || status === "queued" || status === "running") {
    return "warning";
  }
  return "neutral";
}

function formatDate(value?: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function shortUserAgent(userAgent?: string | null) {
  if (!userAgent) {
    return "No user-agent captured";
  }
  const cleaned = userAgent.split(/\s+/).join(" ");
  if (cleaned.length <= 96) {
    return cleaned;
  }
  return `${cleaned.slice(0, 93)}...`;
}

export function GenerationJobsControlPanel() {
  const { tokens } = useAdminAuth();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function refreshJobs() {
    if (!tokens?.access_token) {
      return;
    }

    setIsLoadingJobs(true);
    try {
      const nextJobs = await getGenerationJobs(tokens.access_token);
      setJobs(nextJobs);
      setError(null);
    } catch (nextError) {
      setJobs([]);
      setError(nextError instanceof Error ? nextError.message : "Failed to load generation jobs");
    } finally {
      setIsLoadingJobs(false);
    }
  }

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }

    refreshJobs();
    const timer = window.setInterval(refreshJobs, 5000);
    return () => window.clearInterval(timer);
  }, [tokens?.access_token]);

  async function handleCancel(job: GenerationJob) {
    if (!tokens?.access_token) {
      return;
    }

    setBusyJobId(job.public_id);
    try {
      const nextJob = await cancelGenerationJob(job.public_id, tokens.access_token);
      setJobs((current) => current.map((item) => (item.public_id === nextJob.public_id ? nextJob : item)));
    } finally {
      setBusyJobId(null);
    }
  }

  async function handleDelete(job: GenerationJob) {
    if (!tokens?.access_token) {
      return;
    }
    if (!window.confirm(`Delete job ${job.public_id}?`)) {
      return;
    }

    setBusyJobId(job.public_id);
    try {
      await deleteGenerationJob(job.public_id, tokens.access_token);
      setJobs((current) => current.filter((item) => item.public_id !== job.public_id));
    } finally {
      setBusyJobId(null);
    }
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Generation audit"
        title="Generation jobs"
        description="Operational queue with status, session linkage, current operation, client IP and user-agent visibility."
        action={
          <SoftButton tone="neutral" onClick={refreshJobs} disabled={isLoadingJobs}>
            {isLoadingJobs ? "Refreshing..." : "Refresh queue"}
          </SoftButton>
        }
      />

      {error ? (
        <SurfaceCard variant="soft" padding="sm" className="border-rose-200 bg-rose-50/80">
          <p className="text-sm text-rose-700">{error}</p>
        </SurfaceCard>
      ) : null}

      <div className="grid gap-4">
        {isLoadingJobs && jobs.length === 0 ? (
          <SurfaceCard variant="soft">
            <p className="text-sm text-[var(--text-secondary)]">Loading generation jobs...</p>
          </SurfaceCard>
        ) : null}

        {!isLoadingJobs && !error && jobs.length === 0 ? (
          <SurfaceCard variant="soft">
            <p className="text-sm text-[var(--text-secondary)]">No generation jobs yet.</p>
          </SurfaceCard>
        ) : null}

        {jobs.map((job) => {
          const recentOperations = getRecentOperations(job);
          const lastOperation = getLastOperation(job);

          return (
            <SurfaceCard key={job.id} variant="tinted" padding="md">
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
                <div className="min-w-0 space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <PillBadge tone={statusTone(job.status)}>{job.status}</PillBadge>
                    <PillBadge tone="subtle">{job.provider}</PillBadge>
                    {job.client_ip ? <PillBadge tone="mint">{job.client_ip}</PillBadge> : null}
                  </div>

                  <div>
                    <p className="break-all font-mono text-sm font-semibold text-[var(--text-primary)]">
                      {job.public_id}
                    </p>
                    <p className="mt-1 text-sm text-[var(--text-secondary)]">
                      {job.progress}% - created {formatDate(job.created_at)}
                    </p>
                    {job.session_id ? (
                      <Link
                        href={`/admin/chats?session=${encodeURIComponent(job.session_id)}`}
                        className="mt-1 inline-block break-all text-xs font-medium text-[var(--text-primary)] underline"
                      >
                        session: {job.session_id}
                      </Link>
                    ) : null}
                  </div>

                  <p className="line-clamp-2 text-sm leading-6 text-[var(--text-secondary)]">
                    {job.recommendation_en}
                  </p>

                  {job.error_message ? (
                    <p className="rounded-[18px] border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                      {job.error_message}
                    </p>
                  ) : null}

                  <div className="rounded-[20px] border border-[var(--border-soft)] bg-white/70 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                      Client user-agent
                    </p>
                    <p className="mt-2 text-xs leading-5 text-[var(--text-secondary)]">
                      {shortUserAgent(job.client_user_agent)}
                    </p>
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                      Current operation
                    </p>
                    <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">
                      {lastOperation?.action ?? "No operation log"}
                    </p>
                    {lastOperation ? (
                      <p className="mt-1 text-xs text-[var(--text-muted)]">{formatDate(lastOperation.timestamp)}</p>
                    ) : null}
                  </div>

                  {recentOperations.length > 0 ? (
                    <div className="space-y-2 rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                        Recent trace
                      </p>
                      {recentOperations.map((operation) => (
                        <p
                          key={`${job.public_id}-${operation.timestamp}-${operation.action}`}
                          className="text-xs leading-5 text-[var(--text-secondary)]"
                        >
                          {formatDate(operation.timestamp)} - {operation.action} - {operation.actor}
                        </p>
                      ))}
                    </div>
                  ) : null}

                  <div className="flex flex-wrap gap-2">
                    {job.result_url ? (
                      <Link
                        href={job.result_url}
                        className="rounded-[var(--radius-pill)] border border-[var(--border-soft)] bg-white px-4 py-2 text-sm font-medium text-[var(--text-primary)] transition hover:border-[var(--border-strong)]"
                      >
                        Open result
                      </Link>
                    ) : null}
                    {isActive(job) ? (
                      <SoftButton
                        tone="accent"
                        shape="compact"
                        onClick={() => handleCancel(job)}
                        disabled={busyJobId === job.public_id}
                      >
                        Cancel
                      </SoftButton>
                    ) : null}
                    <SoftButton
                      tone="neutral"
                      shape="compact"
                      onClick={() => handleDelete(job)}
                      disabled={busyJobId === job.public_id}
                    >
                      Delete
                    </SoftButton>
                  </div>
                </div>
              </div>
            </SurfaceCard>
          );
        })}
      </div>
    </div>
  );
}
