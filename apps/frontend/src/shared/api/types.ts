export type Locale = "ru" | "en";
export type ChatMode =
  | "general_advice"
  | "garment_matching"
  | "style_exploration"
  | "occasion_outfit";
export type FlowState =
  | "idle"
  | "awaiting_user_message"
  | "awaiting_anchor_garment"
  | "awaiting_anchor_garment_clarification"
  | "awaiting_occasion_details"
  | "awaiting_occasion_clarification"
  | "awaiting_clarification"
  | "ready_for_decision"
  | "ready_for_generation"
  | "generation_queued"
  | "generation_in_progress"
  | "completed"
  | "recoverable_error";
export type ClarificationKind =
  | "anchor_garment_description"
  | "anchor_garment_missing_attributes"
  | "occasion_event_type"
  | "occasion_time_of_day"
  | "occasion_season"
  | "occasion_dress_code"
  | "occasion_desired_impression"
  | "occasion_missing_multiple_slots"
  | "style_preference"
  | "general_followup";
export type DecisionType =
  | "text_only"
  | "clarification_required"
  | "text_and_generate"
  | "generation_only"
  | "error_recoverable"
  | "error_hard";

export interface CommandContext {
  command_name?: string | null;
  command_step?: string | null;
  metadata: Record<string, unknown>;
}

export interface AnchorGarment {
  raw_user_text?: string | null;
  garment_type?: string | null;
  category?: string | null;
  color_primary?: string | null;
  color_secondary: string[];
  material?: string | null;
  fit?: string | null;
  silhouette?: string | null;
  pattern?: string | null;
  seasonality: string[];
  formality?: string | null;
  gender_context?: string | null;
  style_hints: string[];
  asset_id?: string | null;
  confidence: number;
  completeness_score: number;
  is_sufficient_for_generation: boolean;
  color?: string | null;
  secondary_colors: string[];
}

export interface OccasionContext {
  raw_user_texts: string[];
  event_type?: string | null;
  location?: string | null;
  time_of_day?: string | null;
  season?: string | null;
  dress_code?: string | null;
  weather_context?: string | null;
  desired_impression?: string | null;
  constraints: string[];
  color_preferences: string[];
  garment_preferences: string[];
  comfort_requirements: string[];
  confidence: number;
  completeness_score: number;
  is_sufficient_for_generation: boolean;
}

export interface StyleDirection {
  style_id?: string | null;
  style_name?: string | null;
  style_family?: string | null;
  palette: string[];
  silhouette_family?: string | null;
  hero_garments: string[];
  footwear: string[];
  accessories: string[];
  materials: string[];
  styling_mood: string[];
  composition_type?: string | null;
  background_family?: string | null;
  layout_density?: string | null;
  camera_distance?: string | null;
  visual_preset?: string | null;
  created_at: string;
}

export interface ConversationMemoryItem {
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface GenerationIntent {
  mode: ChatMode;
  trigger: string;
  reason: string;
  must_generate: boolean;
  job_priority: string;
  source_message_id?: number | null;
}

export interface GenerationPayload {
  prompt: string;
  image_brief_en: string;
  recommendation_text: string;
  input_asset_id?: number | null;
  negative_prompt?: string | null;
  visual_preset?: string | null;
  metadata: Record<string, unknown>;
  generation_intent?: GenerationIntent | null;
}

export interface DecisionResult {
  decision_type: DecisionType;
  active_mode: ChatMode;
  flow_state: FlowState;
  text_reply?: string | null;
  generation_payload?: GenerationPayload | null;
  job_id?: string | null;
  context_patch: Record<string, unknown>;
  telemetry: Record<string, unknown>;
  error_code?: string | null;
}

export interface ChatModeContext {
  version: number;
  active_mode: ChatMode;
  requested_intent?: ChatMode | null;
  flow_state: FlowState;
  pending_clarification?: string | null;
  clarification_kind?: ClarificationKind | null;
  clarification_attempts: number;
  should_auto_generate: boolean;
  anchor_garment?: AnchorGarment | null;
  occasion_context?: OccasionContext | null;
  style_history: StyleDirection[];
  last_generation_prompt?: string | null;
  last_generated_outfit_summary?: string | null;
  conversation_memory: ConversationMemoryItem[];
  command_context?: CommandContext | null;
  current_style_id?: string | null;
  current_style_name?: string | null;
  current_job_id?: string | null;
  last_generation_request_key?: string | null;
  last_decision_type?: string | null;
  generation_intent?: GenerationIntent | null;
  updated_at: string;
  updated_by_message_id?: number | null;
}

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

export interface ParserAdminProcess {
  state: "idle" | "running" | "stopping" | string;
  pid?: number | null;
  started_at?: string | null;
  stop_requested_at?: string | null;
  last_exit_code?: number | null;
  last_error?: string | null;
  command?: string | null;
  log_path: string;
  pid_file_path: string;
}

export interface ParserAdminCommands {
  enqueue_command: string;
  worker_command: string;
  combined_command: string;
  stop_command: string;
}

export interface ParserAdminStats {
  styles_total: number;
  source_pages_total: number;
  source_page_versions_total: number;
  style_profiles_total: number;
  style_traits_total: number;
  taxonomy_links_total: number;
  relations_total: number;
  jobs_total: number;
  jobs_queued: number;
  jobs_running: number;
  jobs_succeeded: number;
  jobs_soft_failed: number;
  jobs_hard_failed: number;
  jobs_cooldown_deferred: number;
  runs_total: number;
  runs_completed: number;
  runs_failed: number;
  runs_completed_with_failures: number;
  runs_aborted: number;
}

export interface ParserAdminRecentRun {
  run_id: number;
  source_name: string;
  source_url?: string | null;
  run_status: string;
  styles_seen: number;
  styles_created: number;
  styles_updated: number;
  styles_failed: number;
  started_at: string;
  finished_at?: string | null;
}

export interface ParserAdminOverview {
  process: ParserAdminProcess;
  commands: ParserAdminCommands;
  stats: ParserAdminStats;
  recent_runs: ParserAdminRecentRun[];
  log_tail: string[];
}

export interface ParserAdminStartPayload {
  source_name: string;
  limit: number;
  worker_max_jobs: number;
  title_contains?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface StylistMessageResponse {
  session_id: string;
  recommendation_text: string;
  prompt: string;
  assistant_message: ChatMessage;
  generation_job?: GenerationJob | null;
  timestamp: string;
  decision: DecisionResult;
  session_context: ChatModeContext;
}
