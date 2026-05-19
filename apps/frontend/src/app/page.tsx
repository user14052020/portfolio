import { HomePageSurface } from "@/app/HomePageSurface";
import { getProjectsCached, getSiteSettings } from "@/shared/api/client";
import type { Project } from "@/shared/api/types";
import { fallbackSettings } from "@/shared/mock/content";

export default async function HomePage() {
  const [settingsResult, projectsResult] = await Promise.allSettled([
    getSiteSettings({ cache: "no-store" }),
    getProjectsCached({ featuredOnly: true }, { cache: "no-store" }),
  ]);

  const settings = settingsResult.status === "fulfilled" ? settingsResult.value : fallbackSettings;
  const projects =
    projectsResult.status === "fulfilled"
      ? projectsResult.value.map(encodeProjectDemoUrlForHomepage)
      : [];

  return <HomePageSurface initialSettings={settings} initialProjects={projects} />;
}

function encodeProjectDemoUrlForHomepage(project: Project): Project {
  if (!project.live_url) {
    return project;
  }

  return {
    ...project,
    live_url: Buffer.from(project.live_url, "utf8").toString("base64"),
  };
}
