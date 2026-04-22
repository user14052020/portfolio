"use client";

import Link from "next/link";

import type { AdminChatSessionDetails, ChatMessage, GenerationJob } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

type Props = {
  details: AdminChatSessionDetails | null;
  loading?: boolean;
  selectedSessionId?: string | null;
};

function formatDate(value?: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function roleTone(role: ChatMessage["role"]): "dark" | "accent" | "neutral" {
  if (role === "assistant") {
    return "accent";
  }
  if (role === "system") {
    return "dark";
  }
  return "neutral";
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

export function ChatSessionDetailsPanel({ details, loading = false, selectedSessionId }: Props) {
  if (loading) {
    return (
      <SurfaceCard variant="elevated" className="min-h-[520px]">
        <div className="space-y-4">
          <PillBadge tone="subtle">Loading</PillBadge>
          <p className="text-sm text-[var(--text-secondary)]">
            Pulling session timeline, generation jobs and state snapshot.
          </p>
        </div>
      </SurfaceCard>
    );
  }

  if (!details) {
    return (
      <SurfaceCard variant="elevated" className="min-h-[520px]">
        <div className="space-y-4">
          <PillBadge tone="subtle">No session selected</PillBadge>
          <p className="text-sm text-[var(--text-secondary)]">
            {selectedSessionId
              ? "Session details are unavailable."
              : "Choose a chat session to inspect messages, jobs, IP and runtime state."}
          </p>
        </div>
      </SurfaceCard>
    );
  }

  const session = details.session;

  return (
    <SurfaceCard
      variant="elevated"
      className="min-h-[520px]"
      header={
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <PillBadge tone="dark">Session details</PillBadge>
            {session.client_ip ? <PillBadge tone="mint">{session.client_ip}</PillBadge> : null}
          </div>
          <div>
            <h2 className="break-all font-display text-2xl text-[var(--text-primary)]">{session.session_id}</h2>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Last message {formatDate(session.last_message_at)} - {session.message_count} messages
            </p>
          </div>
        </div>
      }
    >
      <div className="space-y-6">
        <div className="grid gap-3 md:grid-cols-2">
          <AuditField label="Started" value={formatDate(session.started_at)} />
          <AuditField label="Updated" value={formatDate(session.updated_at)} />
          <AuditField label="Mode" value={session.last_active_mode ?? "n/a"} />
          <AuditField label="Decision" value={session.last_decision_type ?? "n/a"} />
        </div>

        <div className="rounded-[24px] border border-[var(--border-soft)] bg-white/70 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">User agent</p>
          <p className="mt-2 break-words text-sm text-[var(--text-secondary)]">
            {session.client_user_agent ?? "n/a"}
          </p>
        </div>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-display text-xl text-[var(--text-primary)]">Messages</h3>
            <PillBadge tone="subtle">{details.messages.length}</PillBadge>
          </div>
          <div className="max-h-[420px] space-y-3 overflow-y-auto pr-1">
            {details.messages.length ? (
              details.messages.map((message) => (
                <div
                  key={message.id}
                  className="rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4"
                >
                  <div className="flex flex-wrap items-center gap-2">
                    <PillBadge tone={roleTone(message.role)} size="sm">
                      {message.role}
                    </PillBadge>
                    <span className="text-xs text-[var(--text-muted)]">{formatDate(message.created_at)}</span>
                    {message.generation_job?.public_id ? (
                      <PillBadge tone="warning" size="sm">
                        {message.generation_job.public_id}
                      </PillBadge>
                    ) : null}
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--text-primary)]">
                    {message.content}
                  </p>
                </div>
              ))
            ) : (
              <p className="rounded-[22px] border border-dashed border-[var(--border-soft)] p-4 text-sm text-[var(--text-secondary)]">
                No messages recorded for this session.
              </p>
            )}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="font-display text-xl text-[var(--text-primary)]">Generation jobs</h3>
            <PillBadge tone="subtle">{details.generation_jobs.length}</PillBadge>
          </div>
          <div className="space-y-3">
            {details.generation_jobs.length ? (
              details.generation_jobs.map((job) => (
                <div key={job.id} className="rounded-[22px] border border-[var(--border-soft)] bg-white/75 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <PillBadge tone={statusTone(job.status)} size="sm">
                      {job.status}
                    </PillBadge>
                    <span className="font-mono text-xs text-[var(--text-secondary)]">{job.public_id}</span>
                    <span className="text-xs text-[var(--text-muted)]">{job.progress}%</span>
                  </div>
                  <p className="mt-2 line-clamp-2 text-sm text-[var(--text-secondary)]">{job.recommendation_en}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs text-[var(--text-muted)]">
                    {job.client_ip ? <span>IP: {job.client_ip}</span> : null}
                    {job.result_url ? (
                      <Link href={job.result_url} className="font-medium text-[var(--text-primary)] underline">
                        Open result
                      </Link>
                    ) : null}
                  </div>
                </div>
              ))
            ) : (
              <p className="rounded-[22px] border border-dashed border-[var(--border-soft)] p-4 text-sm text-[var(--text-secondary)]">
                No generation jobs started from this session.
              </p>
            )}
          </div>
        </section>

        <section className="space-y-3">
          <h3 className="font-display text-xl text-[var(--text-primary)]">State snapshot</h3>
          <pre className="max-h-[280px] overflow-auto rounded-[22px] border border-[var(--border-soft)] bg-[var(--surface-ink)] p-4 text-xs leading-5 text-white/80">
            {JSON.stringify(details.state?.state_payload ?? {}, null, 2)}
          </pre>
        </section>
      </div>
    </SurfaceCard>
  );
}

function AuditField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-[var(--border-soft)] bg-white/70 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium text-[var(--text-primary)]">{value}</p>
    </div>
  );
}
