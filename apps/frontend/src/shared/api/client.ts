import { request } from "@/shared/api/base";
import type { RequestOptions } from "@/shared/api/base";
import type {
  BlogPost,
  ChatModeContext,
  ChatHistoryPage,
  ContactRequest,
  GenerationJob,
  ParserAdminOverview,
  ParserAdminStartPayload,
  Project,
  SiteSettings,
  StylistMessageResponse,
  TokenPair,
  UploadedAsset,
  User
} from "@/shared/api/types";

export async function getSiteSettings(fetchOptions?: Pick<RequestOptions, "cache" | "next">) {
  return request<SiteSettings>("/site-settings", fetchOptions);
}

export async function updateSiteSettings(payload: Record<string, unknown>, token: string) {
  return request<SiteSettings>("/site-settings", {
    method: "PUT",
    token,
    body: JSON.stringify(payload)
  });
}

export async function getProjects(params?: {
  q?: string;
  featuredOnly?: boolean;
  includeDrafts?: boolean;
}, token?: string) {
  return request<Project[]>("/projects", {
    token,
    query: {
      q: params?.q,
      featured_only: params?.featuredOnly,
      include_drafts: params?.includeDrafts
    }
  });
}

export async function getProjectsCached(
  params?: {
    q?: string;
    featuredOnly?: boolean;
    includeDrafts?: boolean;
  },
  fetchOptions?: Pick<RequestOptions, "cache" | "next">
) {
  return request<Project[]>("/projects", {
    ...fetchOptions,
    query: {
      q: params?.q,
      featured_only: params?.featuredOnly,
      include_drafts: params?.includeDrafts
    }
  });
}

export async function getProject(slug: string) {
  return request<Project>(`/projects/${slug}`);
}

export async function createProject(payload: Partial<Project>, token: string) {
  return request<Project>("/projects", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export async function updateProject(id: number, payload: Partial<Project>, token: string) {
  return request<Project>(`/projects/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload)
  });
}

export async function deleteProject(id: number, token: string) {
  return request<void>(`/projects/${id}`, {
    method: "DELETE",
    token
  });
}

export async function getBlogPosts(params?: {
  q?: string;
  categorySlug?: string;
  postType?: string;
  includeDrafts?: boolean;
}, token?: string) {
  return request<BlogPost[]>("/blog-posts", {
    token,
    query: {
      q: params?.q,
      category_slug: params?.categorySlug,
      post_type: params?.postType,
      include_drafts: params?.includeDrafts
    }
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
  return request<BlogPost[]>("/blog-posts", {
    ...fetchOptions,
    query: {
      q: params?.q,
      category_slug: params?.categorySlug,
      post_type: params?.postType,
      include_drafts: params?.includeDrafts
    }
  });
}

export async function getBlogPost(slug: string) {
  return request<BlogPost>(`/blog-posts/${slug}`);
}

export async function createBlogPost(payload: Partial<BlogPost>, token: string) {
  return request<BlogPost>("/blog-posts", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export async function updateBlogPost(id: number, payload: Partial<BlogPost>, token: string) {
  return request<BlogPost>(`/blog-posts/${id}`, {
    method: "PUT",
    token,
    body: JSON.stringify(payload)
  });
}

export async function deleteBlogPost(id: number, token: string) {
  return request<void>(`/blog-posts/${id}`, {
    method: "DELETE",
    token
  });
}

export async function createContactRequest(payload: {
  name: string;
  email: string;
  message: string;
  locale: string;
  source_page?: string;
}) {
  return request<ContactRequest>("/contact-requests", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getContactRequests(token: string) {
  return request<ContactRequest[]>("/contact-requests", { token });
}

export async function updateContactRequest(
  id: number,
  payload: Pick<ContactRequest, "status">,
  token: string
) {
  return request<ContactRequest>(`/contact-requests/${id}`, {
    method: "PATCH",
    token,
    body: JSON.stringify(payload)
  });
}

export async function uploadAsset(
  file: File,
  token?: string,
  relatedEntity?: string,
  relatedEntityId?: number
) {
  const formData = new FormData();
  formData.append("file", file);
  if (relatedEntity) {
    formData.append("related_entity", relatedEntity);
  }
  if (typeof relatedEntityId === "number") {
    formData.append("related_entity_id", String(relatedEntityId));
  }
  const response = await request<{ asset: UploadedAsset }>("/uploads", {
    method: "POST",
    token,
    body: formData
  });
  return response.asset;
}

export async function sendStylistMessage(payload: {
  session_id: string;
  locale: string;
  message?: string;
  asset_id?: number;
  uploaded_asset_id?: number;
  requested_intent?: "general_advice" | "garment_matching" | "style_exploration" | "occasion_outfit";
  command_name?: string;
  command_step?: string;
  metadata?: Record<string, unknown>;
  profile_gender?: string;
  body_height_cm?: number;
  body_weight_kg?: number;
  auto_generate?: boolean;
}) {
  return request<StylistMessageResponse>("/stylist-chat/message", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getChatHistory(sessionId: string) {
  return request<ChatHistoryPage>(`/stylist-chat/history/${sessionId}`, {
    query: {
      limit: 5,
      before_message_id: undefined
    }
  });
}

export async function getChatHistoryPage(
  sessionId: string,
  params?: {
    limit?: number;
    beforeMessageId?: number | null;
  }
) {
  return request<ChatHistoryPage>(`/stylist-chat/history/${sessionId}`, {
    query: {
      limit: params?.limit,
      before_message_id: params?.beforeMessageId ?? undefined
    }
  });
}

export async function getStylistSessionContext(sessionId: string) {
  return request<ChatModeContext>(`/stylist-chat/context/${sessionId}`);
}

export async function createGenerationJob(payload: Record<string, unknown>) {
  return request<GenerationJob>("/generation-jobs", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getGenerationJob(publicId: string) {
  return request<GenerationJob>(`/generation-jobs/${publicId}`);
}

export async function refreshGenerationJobQueue(publicId: string) {
  return request<GenerationJob>(`/generation-jobs/${publicId}/refresh-queue`, {
    method: "POST"
  });
}

export async function getGenerationJobs(token: string) {
  return request<GenerationJob[]>("/generation-jobs", { token });
}

export async function getGenerationJobsBySession(sessionId: string) {
  return request<GenerationJob[]>(`/generation-jobs/session/${sessionId}`);
}

export async function cancelGenerationJob(publicId: string, token: string) {
  return request<GenerationJob>(`/generation-jobs/${publicId}/cancel`, {
    method: "POST",
    token
  });
}

export async function deleteGenerationJob(publicId: string, token: string) {
  return request<GenerationJob>(`/generation-jobs/${publicId}`, {
    method: "DELETE",
    token
  });
}

export async function getStyleIngestionAdminOverview(token: string) {
  return request<ParserAdminOverview>("/style-ingestion-admin/overview", { token });
}

export async function startStyleIngestionWorker(payload: ParserAdminStartPayload, token: string) {
  return request<ParserAdminOverview>("/style-ingestion-admin/start", {
    method: "POST",
    token,
    body: JSON.stringify(payload)
  });
}

export async function stopStyleIngestionWorker(token: string) {
  return request<ParserAdminOverview>("/style-ingestion-admin/stop", {
    method: "POST",
    token
  });
}

export async function loginAdmin(email: string, password: string) {
  return request<TokenPair>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function getCurrentUser(token: string) {
  return request<User>("/auth/me", { token });
}
