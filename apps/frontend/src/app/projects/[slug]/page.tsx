import type { Metadata } from "next";

import { getProject } from "@/shared/api/client";
import { ProjectDetailPage } from "@/widgets/portfolio/ui/ProjectDetailPage";

export async function generateMetadata({
  params
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const { slug } = params;
  const project = await getProject(slug);
  return {
    title: project.seo_title_en ?? project.title_en,
    description: project.seo_description_en ?? project.summary_en
  };
}

export default async function ProjectRoute({
  params
}: {
  params: { slug: string };
}) {
  const { slug } = params;
  const project = await getProject(slug);
  return <ProjectDetailPage project={project} />;
}
