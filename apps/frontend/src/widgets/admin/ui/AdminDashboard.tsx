"use client";

import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getBlogPosts, getContactRequests, getGenerationJobs, getProjects } from "@/shared/api/client";
import { WindowFrame } from "@/shared/ui/WindowFrame";

type DashboardStats = {
  projects: number;
  posts: number;
  contacts: number;
  jobs: number;
};

export function AdminDashboard() {
  const { tokens } = useAdminAuth();
  const [stats, setStats] = useState<DashboardStats>({
    projects: 0,
    posts: 0,
    contacts: 0,
    jobs: 0
  });

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }
    Promise.all([
      getProjects({ includeDrafts: true }, tokens.access_token),
      getBlogPosts({ includeDrafts: true }, tokens.access_token),
      getContactRequests(tokens.access_token),
      getGenerationJobs(tokens.access_token)
    ])
      .then(([projects, posts, contacts, jobs]) => {
        setStats({
          projects: projects.length,
          posts: posts.length,
          contacts: contacts.length,
          jobs: jobs.length
        });
      })
      .catch(() => {
        setStats({
          projects: 0,
          posts: 0,
          contacts: 0,
          jobs: 0
        });
      });
  }, [tokens?.access_token]);

  return (
    <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
      {Object.entries(stats).map(([key, value]) => (
        <WindowFrame key={key} title={key} subtitle="overview">
          <p className="text-5xl font-semibold text-slate-900">{value}</p>
        </WindowFrame>
      ))}
    </div>
  );
}
