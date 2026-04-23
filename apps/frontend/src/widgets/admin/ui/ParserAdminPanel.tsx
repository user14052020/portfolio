"use client";

import { NumberInput, TextInput } from "@mantine/core";
import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import {
  getStyleIngestionAdminOverview,
  startStyleIngestionWorker,
  stopStyleIngestionWorker,
} from "@/shared/api/client";
import type { ParserAdminOverview, ParserAdminRecentRun } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

const DEFAULT_SOURCE_NAME = "aesthetics_wiki";
const DEFAULT_LIMIT = 20;
const DEFAULT_WORKER_MAX_JOBS = 55;
const DEFAULT_PID_FILE_PATH = "/app/media/style_ingestion_admin/style_ingestion_worker.pid";

function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function shellQuote(value: string) {
  return `'${value.replace(/'/g, `'\"'\"'`)}'`;
}

function buildManualCommands(
  form: {
    source_name: string;
    limit: number;
    worker_max_jobs: number;
    title_contains: string;
  },
  pidFilePath: string,
) {
  const titleFilter = form.title_contains.trim()
    ? ` --title-contains ${shellQuote(form.title_contains.trim())}`
    : "";
  const enqueueCommand =
    `docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh ` +
    `--mode enqueue-jobs --source-name ${form.source_name} --limit ${form.limit}${titleFilter}"`;
  const workerCommand =
    `docker compose exec backend sh -lc "cd /app && ./scripts/run_style_ingestion_entrypoint.sh ` +
    `--mode run-worker --source-name ${form.source_name} --worker-max-jobs ${form.worker_max_jobs} --worker-stop-when-idle"`;
  const stopCommand =
    `docker compose exec backend sh -lc "if [ -f ${pidFilePath} ]; then kill -TERM -- -$(cat ${pidFilePath}); fi"`;

  return {
    enqueueCommand,
    workerCommand,
    combinedCommand: `nohup bash -lc ${shellQuote(
      `${enqueueCommand} && ${workerCommand}`,
    )} > ~/style_ingestion_api_worker.log 2>&1 &`,
    stopCommand,
  };
}

function parserStateTone(state: string): "neutral" | "success" | "warning" {
  if (state === "running") {
    return "success";
  }
  if (state === "stopping") {
    return "warning";
  }
  return "neutral";
}

export function ParserAdminPanel() {
  const { tokens } = useAdminAuth();
  const [overview, setOverview] = useState<ParserAdminOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"start" | "stop" | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const [form, setForm] = useState({
    source_name: DEFAULT_SOURCE_NAME,
    limit: DEFAULT_LIMIT,
    worker_max_jobs: DEFAULT_WORKER_MAX_JOBS,
    title_contains: "",
  });

  async function refreshOverview() {
    if (!tokens?.access_token) {
      return;
    }
    try {
      const nextOverview = await getStyleIngestionAdminOverview(tokens.access_token);
      setOverview(nextOverview);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to load parser overview");
    }
  }

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }
    void refreshOverview();
    const timer = window.setInterval(() => {
      void refreshOverview();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [tokens?.access_token]);

  const commands = useMemo(() => {
    return buildManualCommands(form, overview?.process.pid_file_path ?? DEFAULT_PID_FILE_PATH);
  }, [form, overview?.process.pid_file_path]);

  async function copyCommand(key: string, value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopiedKey(key);
      window.setTimeout(() => {
        setCopiedKey((current) => (current === key ? null : current));
      }, 1500);
    } catch {
      setCopiedKey(null);
    }
  }

  async function handleStart() {
    if (!tokens?.access_token) {
      return;
    }
    setBusyAction("start");
    try {
      const nextOverview = await startStyleIngestionWorker(
        {
          source_name: form.source_name,
          limit: form.limit,
          worker_max_jobs: form.worker_max_jobs,
          title_contains: form.title_contains.trim() || null,
        },
        tokens.access_token,
      );
      setOverview(nextOverview);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to start parser");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleStop() {
    if (!tokens?.access_token) {
      return;
    }
    setBusyAction("stop");
    try {
      const nextOverview = await stopStyleIngestionWorker(tokens.access_token);
      setOverview(nextOverview);
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to stop parser");
    } finally {
      setBusyAction(null);
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <ParserAdminHeader />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to start workers, inspect parser state, and copy operational commands.
        </p>
      </SurfaceCard>
    );
  }

  const stats = overview?.stats;
  const process = overview?.process;
  const parserIsBusy = process?.state === "running" || process?.state === "stopping";

  return (
    <div className="space-y-6">
      <SurfaceCard
        variant="elevated"
        header={
          <SectionHeader
            eyebrow="Parser operations"
            title="Style ingestion control"
            description="Start the enqueue-and-worker flow, watch process state, and keep manual commands visible for terminal fallback."
            action={
              <div className="flex flex-wrap gap-2">
                <SoftButton tone="dark" onClick={handleStart} disabled={parserIsBusy || busyAction === "start"}>
                  {busyAction === "start" ? "Starting..." : "Start parser"}
                </SoftButton>
                <SoftButton tone="accent" onClick={handleStop} disabled={!process || process.state === "idle" || busyAction === "stop"}>
                  {busyAction === "stop" ? "Stopping..." : "Stop parser"}
                </SoftButton>
                <SoftButton tone="neutral" onClick={() => void refreshOverview()}>
                  Refresh
                </SoftButton>
              </div>
            }
          />
        }
      >
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <ParserMetric
                label="Process state"
                value={process?.state ?? "idle"}
                badge={
                  <PillBadge tone={parserStateTone(process?.state ?? "idle")} size="sm">
                    pid {process?.pid ?? "-"}
                  </PillBadge>
                }
              />
              <ParserMetric label="Loaded styles" value={String(stats?.styles_total ?? 0)} />
              <ParserMetric label="Queued jobs" value={String(stats?.jobs_queued ?? 0)} />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <TextInput
                label="Source name"
                value={form.source_name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    source_name: event.currentTarget.value.trim() || DEFAULT_SOURCE_NAME,
                  }))
                }
              />
              <TextInput
                label="Title filter"
                placeholder="Optional partial title"
                value={form.title_contains}
                onChange={(event) =>
                  setForm((current) => ({ ...current, title_contains: event.currentTarget.value }))
                }
              />
              <NumberInput
                label="Enqueue limit"
                min={1}
                max={500}
                value={form.limit}
                onChange={(value) =>
                  setForm((current) => ({ ...current, limit: Number(value) || DEFAULT_LIMIT }))
                }
              />
              <NumberInput
                label="Worker max jobs"
                min={1}
                max={1000}
                value={form.worker_max_jobs}
                onChange={(value) =>
                  setForm((current) => ({
                    ...current,
                    worker_max_jobs: Number(value) || DEFAULT_WORKER_MAX_JOBS,
                  }))
                }
              />
            </div>

            {error ? (
              <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
                {error}
              </div>
            ) : null}
          </div>

          <div className="rounded-[28px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5">
            <div className="mb-4 flex flex-wrap gap-2">
              <PillBadge tone="dark">Process detail</PillBadge>
              <PillBadge tone="subtle">auto refresh 5s</PillBadge>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <ProcessDetail label="Started at" value={formatDateTime(process?.started_at)} />
              <ProcessDetail label="Stop requested" value={formatDateTime(process?.stop_requested_at)} />
              <ProcessDetail label="Last exit code" value={String(process?.last_exit_code ?? "-")} />
              <ProcessDetail label="Last error" value={process?.last_error ?? "-"} />
              <ProcessDetail label="Log file" value={process?.log_path ?? "-"} />
              <ProcessDetail label="Pid file" value={process?.pid_file_path ?? "-"} />
            </div>
          </div>
        </div>
      </SurfaceCard>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <SurfaceCard
          variant="default"
          header={
            <SectionHeader
              eyebrow="Recent runs"
              title="Ingestion history"
              description="Latest style_ingest_runs with source and outcome counters."
            />
          }
        >
          <div className="space-y-3">
            {(overview?.recent_runs ?? []).map((run) => (
              <RecentRunCard key={run.run_id} run={run} />
            ))}
            {overview?.recent_runs?.length === 0 ? (
              <p className="text-sm text-[var(--text-secondary)]">No parser runs yet.</p>
            ) : null}
          </div>
        </SurfaceCard>

        <SurfaceCard
          variant="ink"
          header={
            <div className="space-y-2">
              <PillBadge tone="neutral">Worker log</PillBadge>
              <h2 className="font-display text-3xl text-[var(--text-inverse)]">Live tail</h2>
              <p className="text-sm text-white/70">Tail of the admin-run parser log.</p>
            </div>
          }
        >
          <pre className="max-h-[520px] overflow-auto rounded-[22px] border border-white/10 bg-black/35 p-4 text-xs leading-6 text-white/85">
            {(overview?.log_tail ?? []).join("\n") || "No log entries yet."}
          </pre>
        </SurfaceCard>
      </div>

      <SurfaceCard
        variant="tinted"
        header={
          <SectionHeader
            eyebrow="Pipeline stats"
            title="Catalog and queue health"
            description="Canonical style catalog counters plus queue state for operational checks."
          />
        }
      >
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {[
            ["Source pages", stats?.source_pages_total ?? 0],
            ["Page versions", stats?.source_page_versions_total ?? 0],
            ["Profiles", stats?.style_profiles_total ?? 0],
            ["Traits", stats?.style_traits_total ?? 0],
            ["Taxonomy links", stats?.taxonomy_links_total ?? 0],
            ["Relations", stats?.relations_total ?? 0],
            ["Succeeded jobs", stats?.jobs_succeeded ?? 0],
            ["Running jobs", stats?.jobs_running ?? 0],
            ["Soft failed jobs", stats?.jobs_soft_failed ?? 0],
            ["Hard failed jobs", stats?.jobs_hard_failed ?? 0],
            ["Cooldown deferred", stats?.jobs_cooldown_deferred ?? 0],
            ["Runs total", stats?.runs_total ?? 0],
          ].map(([label, value]) => (
            <ParserMetric key={String(label)} label={String(label)} value={String(value)} />
          ))}
        </div>
      </SurfaceCard>

      <SurfaceCard
        variant="default"
        header={
          <SectionHeader
            eyebrow="Manual fallback"
            title="Equivalent terminal commands"
            description="Copy these when the UI needs to be mirrored from the terminal."
          />
        }
      >
        <div className="space-y-4">
          {[
            ["enqueue", "Enqueue jobs", commands.enqueueCommand],
            ["worker", "Run worker", commands.workerCommand],
            ["combined", "Start in background", commands.combinedCommand],
            ["stop", "Stop running worker", commands.stopCommand],
          ].map(([key, label, value]) => (
            <CommandBlock
              key={String(key)}
              label={String(label)}
              value={String(value)}
              isCopied={copiedKey === key}
              onCopy={() => void copyCommand(String(key), String(value))}
            />
          ))}
          {process?.command ? (
            <CommandBlock
              label="Current backend command"
              value={process.command}
              isCopied={copiedKey === "current"}
              onCopy={() => void copyCommand("current", process.command ?? "")}
            />
          ) : null}
        </div>
      </SurfaceCard>
    </div>
  );
}

function ParserAdminHeader() {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <PillBadge tone="dark">Parser operations</PillBadge>
        <PillBadge tone="accent">Style ingestion</PillBadge>
      </div>
      <div>
        <h2 className="font-display text-2xl text-[var(--text-primary)]">Style ingestion control</h2>
        <p className="mt-1 max-w-2xl text-sm text-[var(--text-secondary)]">
          Operational controls for enqueue jobs, worker execution, queue health, and manual terminal fallback.
        </p>
      </div>
    </div>
  );
}

function ParserMetric({
  label,
  value,
  badge,
}: {
  label: string;
  value: string;
  badge?: ReactNode;
}) {
  return (
    <div className="rounded-[24px] border border-[var(--border-soft)] bg-white/75 p-4 shadow-[var(--shadow-soft-sm)]">
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
        {badge}
      </div>
      <p className="mt-3 break-words font-display text-3xl leading-none text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function ProcessDetail({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[20px] border border-[var(--border-soft)] bg-white/65 p-4">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
      <p className="mt-2 break-words text-sm text-[var(--text-secondary)]">{value}</p>
    </div>
  );
}

function RecentRunCard({ run }: { run: ParserAdminRecentRun }) {
  return (
    <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-[var(--text-primary)]">run #{run.run_id}</p>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">{formatDateTime(run.started_at)}</p>
        </div>
        <PillBadge tone={run.run_status === "succeeded" ? "success" : "neutral"} size="sm">
          {run.run_status}
        </PillBadge>
      </div>
      <div className="mt-4 grid gap-2 text-sm text-[var(--text-secondary)] sm:grid-cols-3">
        <span>created {run.styles_created}</span>
        <span>updated {run.styles_updated}</span>
        <span>failed {run.styles_failed}</span>
      </div>
      {run.source_url ? <p className="mt-3 break-all text-xs text-[var(--text-muted)]">{run.source_url}</p> : null}
    </div>
  );
}

function CommandBlock({
  label,
  value,
  isCopied,
  onCopy,
}: {
  label: string;
  value: string;
  isCopied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="font-semibold text-[var(--text-primary)]">{label}</p>
        <SoftButton tone="neutral" shape="compact" onClick={onCopy}>
          {isCopied ? "Copied" : "Copy"}
        </SoftButton>
      </div>
      <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-[20px] bg-[var(--surface-ink)] p-4 text-xs leading-6 text-[var(--text-inverse)]">
        {value}
      </pre>
    </div>
  );
}
