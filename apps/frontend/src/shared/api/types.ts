export type Locale = "ru" | "en";

export type MediaType = "image" | "video" | "model3d";
export type BlogPostType = "article" | "video";
export type GenerationStatus = "pending" | "queued" | "running" | "completed" | "failed" | "cancelled";

export interface GenerationJobOperation {
  timestamp: string;
  action: string;
  actor: string;
  details: Record<string, unknown>;
}

export interface Role {
  id: number;
  name: string;
  description?: string | null;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  role: Role;
  created_at: string;
  updated_at: string;
}

export interface UploadedAsset {
  id: number;
  original_filename: string;
  storage_path: string;
  public_url: string;
  mime_type: string;
  size_bytes: number;
  asset_type: string;
  storage_backend: string;
  related_entity?: string | null;
  related_entity_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMedia {
  id: number;
  asset_type: MediaType;
  url: string;
  alt_ru?: string | null;
  alt_en?: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  slug: string;
  title_ru: string;
  title_en: string;
  summary_ru: string;
  summary_en: string;
  description_ru: string;
  description_en: string;
  stack: string[];
  cover_image?: string | null;
  preview_video_url?: string | null;
  repository_url?: string | null;
  live_url?: string | null;
  page_scene_key?: string | null;
  seo_title_ru?: string | null;
  seo_title_en?: string | null;
  seo_description_ru?: string | null;
  seo_description_en?: string | null;
  sort_order: number;
  is_featured: boolean;
  is_published: boolean;
  media_items: ProjectMedia[];
  created_at: string;
  updated_at: string;
}

export interface BlogCategory {
  id: number;
  slug: string;
  name_ru: string;
  name_en: string;
  created_at: string;
  updated_at: string;
}

export interface BlogPost {
  id: number;
  slug: string;
  title_ru: string;
  title_en: string;
  excerpt_ru: string;
  excerpt_en: string;
  content_ru: string;
  content_en: string;
  cover_image?: string | null;
  video_url?: string | null;
  post_type: BlogPostType;
  tags: string[];
  seo_title_ru?: string | null;
  seo_title_en?: string | null;
  seo_description_ru?: string | null;
  seo_description_en?: string | null;
  page_scene_key?: string | null;
  is_published: boolean;
  published_at?: string | null;
  category?: BlogCategory | null;
  created_at: string;
  updated_at: string;
}

export interface SiteSettings {
  id: number;
  brand_name: string;
  contact_email: string;
  contact_phone?: string | null;
  assistant_name_ru: string;
  assistant_name_en: string;
  hero_title_ru: string;
  hero_title_en: string;
  hero_subtitle_ru: string;
  hero_subtitle_en: string;
  about_title_ru: string;
  about_title_en: string;
  about_text_ru: string;
  about_text_en: string;
  socials: Record<string, string>;
  skills: string[];
  created_at: string;
  updated_at: string;
}

export interface GenerationJob {
  id: number;
  public_id: string;
  session_id?: string | null;
  provider: "comfyui" | "mock";
  status: GenerationStatus;
  input_text?: string | null;
  prompt: string;
  recommendation_ru: string;
  recommendation_en: string;
  input_asset?: UploadedAsset | null;
  result_url?: string | null;
  external_job_id?: string | null;
  progress: number;
  body_height_cm?: number | null;
  body_weight_kg?: number | null;
  error_message?: string | null;
  provider_payload: Record<string, unknown>;
  operation_log: GenerationJobOperation[];
  started_at?: string | null;
  completed_at?: string | null;
  deleted_at?: string | null;
  queue_position?: number | null;
  queue_ahead?: number | null;
  queue_total?: number | null;
  queue_refresh_available_at?: string | null;
  queue_refresh_retry_after_seconds?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  session_id: string;
  role: "user" | "assistant" | "system";
  locale: string;
  content: string;
  generation_job_id?: number | null;
  generation_job?: GenerationJob | null;
  uploaded_asset?: UploadedAsset | null;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryPage {
  items: ChatMessage[];
  has_more: boolean;
  next_before_message_id?: number | null;
}

export interface ContactRequest {
  id: number;
  name: string;
  email: string;
  message: string;
  locale: string;
  source_page?: string | null;
  status: "new" | "in_progress" | "closed";
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface StylistMessageResponse {
  session_id: string;
  recommendation_text: string;
  recommendation_text_ru: string;
  recommendation_text_en: string;
  prompt: string;
  assistant_message: ChatMessage;
  generation_job?: GenerationJob | null;
  timestamp: string;
}
