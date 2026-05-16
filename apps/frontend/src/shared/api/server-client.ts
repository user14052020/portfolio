import { requestFromServer } from "@/shared/api/server-base";
import type { RequestOptions } from "@/shared/api/request-core";
import type { BlogPost, Project, SiteSettings } from "@/shared/api/types";

export async function getSiteSettings(fetchOptions?: Pick<RequestOptions, "cache" | "next">) {
  return requestFromServer<SiteSettings>("/site-settings", fetchOptions);
}

export async function getProjectsCached(
  params?: {
    q?: string;
    featuredOnly?: boolean;
    includeDrafts?: boolean;
  },
  fetchOptions?: Pick<RequestOptions, "cache" | "next">
) {
  return requestFromServer<Project[]>("/projects", {
    ...fetchOptions,
    query: {
      q: params?.q,
      featured_only: params?.featuredOnly,
      include_drafts: params?.includeDrafts,
    },
  });
}

export async function getBlogPostsCached(
  params?: {
    q?: string;
    categorySlug?: string;
    postType?: string;
    includeDrafts?: boolean;
  },
  fetchOptions?: Pick<RequestOptions, "cache" | "next">
) {
  return requestFromServer<BlogPost[]>("/blog-posts", {
    ...fetchOptions,
    query: {
      q: params?.q,
      category_slug: params?.categorySlug,
      post_type: params?.postType,
      include_drafts: params?.includeDrafts,
    },
  });
}

export async function getProject(slug: string) {
  return requestFromServer<Project>(`/projects/${slug}`);
}

export async function getBlogPost(slug: string) {
  return requestFromServer<BlogPost>(`/blog-posts/${slug}`);
}
