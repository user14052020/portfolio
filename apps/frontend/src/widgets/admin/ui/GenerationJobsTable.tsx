"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getGenerationJobs } from "@/shared/api/client";
import type { GenerationJob } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function GenerationJobsTable() {
  const { tokens } = useAdminAuth();
  const [jobs, setJobs] = useState<GenerationJob[]>([]);

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }
    getGenerationJobs(tokens.access_token)
      .then(setJobs)
      .catch(() => setJobs([]));
  }, [tokens?.access_token]);

  return (
    <WindowFrame title="Generation jobs" subtitle="AI stylist queue">
      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-slate-900">{job.public_id}</p>
                <p className="text-sm text-slate-500">
                  {job.status} · {job.progress}%
                </p>
              </div>
              {job.result_url ? (
                <Link href={job.result_url} className="text-sm text-slate-700 underline">
                  Open result
                </Link>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </WindowFrame>
  );
}
