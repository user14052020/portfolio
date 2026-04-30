export const FRONTEND_PRESENTATION_PROFILES = [
  "feminine",
  "masculine",
  "androgynous",
  "unisex",
] as const;

export const FRONTEND_FIT_PREFERENCES = ["fitted", "relaxed", "oversized", "balanced"] as const;

export const FRONTEND_SILHOUETTE_PREFERENCES = [
  "elongated",
  "soft",
  "structured",
  "minimal",
  "layered",
  "voluminous_top",
  "balanced_proportions",
] as const;

export const FRONTEND_COMFORT_PREFERENCES = [
  "high_comfort",
  "balanced",
  "style_first",
] as const;

export const FRONTEND_FORMALITY_PREFERENCES = [
  "casual",
  "smart_casual",
  "refined",
  "formal",
] as const;

export type FrontendPresentationProfile =
  (typeof FRONTEND_PRESENTATION_PROFILES)[number];
export type FrontendFitPreference = (typeof FRONTEND_FIT_PREFERENCES)[number];
export type FrontendSilhouettePreference =
  (typeof FRONTEND_SILHOUETTE_PREFERENCES)[number];
export type FrontendComfortPreference =
  (typeof FRONTEND_COMFORT_PREFERENCES)[number];
export type FrontendFormalityPreference =
  (typeof FRONTEND_FORMALITY_PREFERENCES)[number];

export interface FrontendProfileContext {
  presentation_profile?: FrontendPresentationProfile | null;
  fit_preferences?: FrontendFitPreference[];
  silhouette_preferences?: FrontendSilhouettePreference[];
  comfort_preferences?: FrontendComfortPreference[];
  formality_preferences?: FrontendFormalityPreference[];
  color_preferences?: string[];
  color_avoidances?: string[];
  preferred_items?: string[];
  avoided_items?: string[];
  [key: string]: unknown;
}

export type FrontendProfileUpdate = Partial<FrontendProfileContext>;
