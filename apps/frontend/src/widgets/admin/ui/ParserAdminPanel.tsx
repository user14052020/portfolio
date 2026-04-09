"use client";

import { Button, NumberInput, TextInput } from "@mantine/core";
import { useEffect, useMemo, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import {
  getStyleIngestionAdminOverview,
  startStyleIngestionWorker,
  stopStyleIngestionWorker
} from "@/shared/api/client";
import type { ParserAdminOverview } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

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
  pidFilePath: string
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
      `${enqueueCommand} && ${workerCommand}`
    )} > ~/style_ingestion_api_worker.log 2>&1 &`,
    stopCommand
  };
}

function parserStateTone(state: string) {
  if (state === "running") {
    return "bg-emerald-100 text-emerald-700";
  }
  if (state === "stopping") {
    return "bg-amber-100 text-amber-700";
  }
  return "bg-slate-100 text-slate-700";
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
    title_contains: ""
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
    return buildManualCommands(
      form,
      overview?.process.pid_file_path ?? DEFAULT_PID_FILE_PATH
    );
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
          title_contains: form.title_contains.trim() || null
        },
        tokens.access_token
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

  const stats = overview?.stats;
  const process = overview?.process;
  const parserIsBusy = process?.state === "running" || process?.state === "stopping";

  return (
    <div className="space-y-6">
      <WindowFrame title="Parser control" subtitle="API-first enqueue-jobs plus run-worker flow">
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-5">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Process state</p>
                <div className="mt-3 flex items-center gap-3">
                  <span
                    className={`rounded-full px-3 py-1 text-xs font-medium ${parserStateTone(process?.state ?? "idle")}`}
                  >
                    {process?.state ?? "idle"}
                  </span>
                  <span className="text-sm text-slate-500">pid: {process?.pid ?? "-"}</span>
                </div>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Loaded styles</p>
                <p className="mt-3 text-3xl font-semibold text-slate-900">{stats?.styles_total ?? 0}</p>
              </div>
              <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Queued jobs</p>
                <p className="mt-3 text-3xl font-semibold text-slate-900">{stats?.jobs_queued ?? 0}</p>
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <TextInput
                label="Source name"
                value={form.source_name}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    source_name: event.currentTarget.value.trim() || DEFAULT_SOURCE_NAME
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
                    worker_max_jobs: Number(value) || DEFAULT_WORKER_MAX_JOBS
                  }))
                }
              />
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                radius="xl"
                onClick={handleStart}
                loading={busyAction === "start"}
                disabled={parserIsBusy}
              >
                Start parser
              </Button>
              <Button
                radius="xl"
                variant="light"
                color="red"
                onClick={handleStop}
                loading={busyAction === "stop"}
                disabled={process?.state === "idle"}
              >
                Stop parser
              </Button>
              <Button radius="xl" variant="default" onClick={() => void refreshOverview()}>
                Refresh
              </Button>
            </div>

            {error ? <p className="text-sm text-rose-600">{error}</p> : null}
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-slate-50 p-5">
            <div className="space-y-3">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Started at</p>
                <p className="mt-1 text-sm text-slate-700">{formatDateTime(process?.started_at)}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Stop requested</p>
                <p className="mt-1 text-sm text-slate-700">{formatDateTime(process?.stop_requested_at)}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last exit code</p>
                <p className="mt-1 text-sm text-slate-700">{process?.last_exit_code ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last error</p>
                <p className="mt-1 break-words text-sm text-slate-700">{process?.last_error ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Log file</p>
                <p className="mt-1 break-all text-sm text-slate-700">{process?.log_path ?? "-"}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Pid file</p>
                <p className="mt-1 break-all text-sm text-slate-700">{process?.pid_file_path ?? "-"}</p>
              </div>
            </div>
          </div>
        </div>
      </WindowFrame>

      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <WindowFrame title="Recent runs" subtitle="Latest style_ingest_runs">
          <div className="space-y-3">
            {(overview?.recent_runs ?? []).map((run) => (
              <div key={run.run_id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-medium text-slate-900">run #{run.run_id} - {run.run_status}</p>
                    <p className="text-sm text-slate-500">{formatDateTime(run.started_at)}</p>
                  </div>
                  <div className="text-sm text-slate-600">
                    created {run.styles_created} - updated {run.styles_updated} - failed {run.styles_failed}
                  </div>
                </div>
                {run.source_url ? <p className="mt-2 break-all text-xs text-slate-500">{run.source_url}</p> : null}
              </div>
            ))}
            {overview?.recent_runs?.length === 0 ? (
              <p className="text-sm text-slate-500">No parser runs yet.</p>
            ) : null}
          </div>
        </WindowFrame>

        <WindowFrame title="Worker log" subtitle="Tail of the admin-run parser log">
          <pre className="max-h-[520px] overflow-auto rounded-[18px] bg-slate-950 p-4 text-xs leading-6 text-slate-100">
            {(overview?.log_tail ?? []).join("\n") || "No log entries yet."}
          </pre>
        </WindowFrame>
      </div>

      <WindowFrame title="Pipeline stats" subtitle="Canonical catalog and queue health">
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
            ["Runs total", stats?.runs_total ?? 0]
          ].map(([label, value]) => (
            <div key={String(label)} className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm text-slate-500">{label}</p>
              <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
            </div>
          ))}
        </div>
      </WindowFrame>

      <WindowFrame title="Manual commands" subtitle="Equivalent terminal commands">
        <div className="space-y-4">
          {[
            ["enqueue", "Enqueue jobs", commands.enqueueCommand],
            ["worker", "Run worker", commands.workerCommand],
            ["combined", "Start in background", commands.combinedCommand],
            ["stop", "Stop running worker", commands.stopCommand]
          ].map(([key, label, value]) => (
            <div key={String(key)} className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="font-medium text-slate-900">{label}</p>
                <button
                  type="button"
                  onClick={() => void copyCommand(String(key), String(value))}
                  className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700"
                >
                  {copiedKey === key ? "Copied" : "Copy"}
                </button>
              </div>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-[18px] bg-slate-900 p-4 text-xs leading-6 text-slate-100">
                {value}
              </pre>
            </div>
          ))}
          {process?.command ? (
            <div className="rounded-[22px] border border-slate-200 bg-slate-50 p-4">
              <p className="mb-3 font-medium text-slate-900">Current backend command</p>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all rounded-[18px] bg-slate-900 p-4 text-xs leading-6 text-slate-100">
                {process.command}
              </pre>
            </div>
          ) : null}
        </div>
      </WindowFrame>
    </div>
  );
}
