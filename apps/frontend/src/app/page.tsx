import { HomePageSurface } from "@/app/HomePageSurface";
import { getProjectsCached, getSiteSettings } from "@/shared/api/client";
import { fallbackProjects, fallbackSettings } from "@/shared/mock/content";

export default async function HomePage() {
  try {
    const [settings, projects] = await Promise.all([
      getSiteSettings({ next: { revalidate: 60 } }),
      getProjectsCached({ featuredOnly: true }, { next: { revalidate: 60 } }),
    ]);

    return <HomePageSurface initialSettings={settings} initialProjects={projects} />;
  } catch {
    return <HomePageSurface initialSettings={fallbackSettings} initialProjects={fallbackProjects} />;
  }
}
