"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { cancelGenerationJob, deleteGenerationJob, getGenerationJobs } from "@/shared/api/client";
import type { GenerationJob } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

function isActive(job: GenerationJob) {
  return job.status === "pending" || job.status === "queued" || job.status === "running";
}

function getRecentOperations(job: GenerationJob) {
  return job.operation_log.slice(-3).reverse();
}

export function GenerationJobsControlPanel() {
  const { tokens } = useAdminAuth();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);

  async function refreshJobs() {
    if (!tokens?.access_token) {
      return;
    }

    try {
      const nextJobs = await getGenerationJobs(tokens.access_token);
      setJobs(nextJobs);
    } catch {
      setJobs([]);
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
    <WindowFrame title="Generation jobs" subtitle="AI stylist queue">
      <div className="space-y-3">
        {jobs.map((job) => {
          const recentOperations = getRecentOperations(job);

          return (
            <div key={job.id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <p className="font-medium text-slate-900">{job.public_id}</p>
                  <p className="text-sm text-slate-500">{job.status} / {job.progress}%</p>
                  {job.session_id ? <p className="mt-1 text-xs text-slate-500">session: {job.session_id}</p> : null}
                  {job.error_message ? <p className="mt-2 text-sm text-rose-600">{job.error_message}</p> : null}
                  {recentOperations.length > 0 ? (
                    <div className="mt-3 space-y-1 border-l border-slate-200 pl-3">
                      {recentOperations.map((operation) => (
                        <p key={`${job.public_id}-${operation.timestamp}-${operation.action}`} className="text-xs text-slate-500">
                          {operation.timestamp} / {operation.action} / {operation.actor}
                        </p>
                      ))}
                    </div>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {job.result_url ? (
                    <Link href={job.result_url} className="text-sm text-slate-700 underline">
                      Open result
                    </Link>
                  ) : null}
                  {isActive(job) ? (
                    <button
                      type="button"
                      onClick={() => handleCancel(job)}
                      disabled={busyJobId === job.public_id}
                      className="rounded-full border border-amber-300 px-3 py-1 text-sm text-amber-700 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => handleDelete(job)}
                    disabled={busyJobId === job.public_id}
                    className="rounded-full border border-rose-300 px-3 py-1 text-sm text-rose-700 disabled:opacity-50"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </WindowFrame>
  );
}
