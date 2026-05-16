import type { Locale } from "@/shared/api/types";

import {
  FRONTEND_COMFORT_PREFERENCES,
  FRONTEND_FIT_PREFERENCES,
  FRONTEND_FORMALITY_PREFERENCES,
  FRONTEND_PRESENTATION_PROFILES,
  FRONTEND_SILHOUETTE_PREFERENCES,
  type FrontendComfortPreference,
  type FrontendFitPreference,
  type FrontendFormalityPreference,
  type FrontendPresentationProfile,
  type FrontendProfileContext,
  type FrontendProfileUpdate,
  type FrontendSilhouettePreference,
} from "./types";

const PROFILE_CONTEXT_STORAGE_KEY = "portfolio-chat-profile-context";
const MAX_CATEGORICAL_ITEMS = 4;
const MAX_OPEN_TEXT_ITEMS = 8;

const presentationProfileSet = new Set<string>(FRONTEND_PRESENTATION_PROFILES);
const fitPreferenceSet = new Set<string>(FRONTEND_FIT_PREFERENCES);
const silhouettePreferenceSet = new Set<string>(FRONTEND_SILHOUETTE_PREFERENCES);
const comfortPreferenceSet = new Set<string>(FRONTEND_COMFORT_PREFERENCES);
const formalityPreferenceSet = new Set<string>(FRONTEND_FORMALITY_PREFERENCES);
const knownProfileContextKeys = new Set<string>([
  "presentation_profile",
  "fit_preferences",
  "silhouette_preferences",
  "comfort_preferences",
  "formality_preferences",
  "color_preferences",
  "color_avoidances",
  "preferred_items",
  "avoided_items",
]);

type ClarificationSuggestion = {
  label: string;
  draft: string;
};

export function normalizeProfileContext(value: unknown): FrontendProfileContext {
  const payload = isRecord(value) ? value : {};
  const presentationProfile = normalizePresentationProfile(payload.presentation_profile);

  const normalized: FrontendProfileContext = collectProfileExtensionFields(payload);
  if (presentationProfile) {
    normalized.presentation_profile = presentationProfile;
  }

  const fitPreferences = normalizeClosedSet<FrontendFitPreference>(
    payload.fit_preferences,
    fitPreferenceSet,
    {
      tailored: "fitted",
      slim: "fitted",
      close_fit: "fitted",
      loose: "relaxed",
      roomy: "relaxed",
      oversize: "oversized",
      regular: "balanced",
      "приталенный": "fitted",
      "расслабленный": "relaxed",
      "свободный": "relaxed",
      "оверсайз": "oversized",
      "сбалансированный": "balanced",
    },
    MAX_CATEGORICAL_ITEMS,
  );
  if (fitPreferences.length > 0) {
    normalized.fit_preferences = fitPreferences;
  }

  const silhouettePreferences = normalizeClosedSet<FrontendSilhouettePreference>(
    payload.silhouette_preferences,
    silhouettePreferenceSet,
    {
      balance: "balanced_proportions",
      balanced: "balanced_proportions",
      balanced_proportions: "balanced_proportions",
      "balanced proportions": "balanced_proportions",
      voluminous_top: "voluminous_top",
      "voluminous top": "voluminous_top",
      "мягкий": "soft",
      "структурный": "structured",
      "структурированный": "structured",
      "вытянутый": "elongated",
      "многослойный": "layered",
      "минималистичный": "minimal",
    },
    MAX_CATEGORICAL_ITEMS,
  );
  if (silhouettePreferences.length > 0) {
    normalized.silhouette_preferences = silhouettePreferences;
  }

  const comfortPreferences = normalizeClosedSet<FrontendComfortPreference>(
    payload.comfort_preferences,
    comfortPreferenceSet,
    {
      comfortable: "high_comfort",
      comfort_first: "high_comfort",
      "comfort first": "high_comfort",
      "style first": "style_first",
      "style-first": "style_first",
      "максимально комфортно": "high_comfort",
      "комфортно": "high_comfort",
      "баланс": "balanced",
      "выразительно": "style_first",
    },
    MAX_CATEGORICAL_ITEMS,
  );
  if (comfortPreferences.length > 0) {
    normalized.comfort_preferences = comfortPreferences;
  }

  const formalityPreferences = normalizeClosedSet<FrontendFormalityPreference>(
    payload.formality_preferences,
    formalityPreferenceSet,
    {
      "smart casual": "smart_casual",
      "smart-casual": "smart_casual",
      polished: "refined",
      elevated: "refined",
      dressy: "formal",
      "смарт кэжуал": "smart_casual",
      "умеренно формально": "refined",
    },
    MAX_CATEGORICAL_ITEMS,
  );
  if (formalityPreferences.length > 0) {
    normalized.formality_preferences = formalityPreferences;
  }

  const colorPreferences = normalizeOpenTextSet(payload.color_preferences, MAX_OPEN_TEXT_ITEMS);
  if (colorPreferences.length > 0) {
    normalized.color_preferences = colorPreferences;
  }

  const colorAvoidances = normalizeOpenTextSet(payload.color_avoidances, MAX_OPEN_TEXT_ITEMS);
  if (colorAvoidances.length > 0) {
    normalized.color_avoidances = colorAvoidances;
  }

  const preferredItems = normalizeOpenTextSet(payload.preferred_items, MAX_OPEN_TEXT_ITEMS);
  if (preferredItems.length > 0) {
    normalized.preferred_items = preferredItems;
  }

  const avoidedItems = normalizeOpenTextSet(payload.avoided_items, MAX_OPEN_TEXT_ITEMS);
  if (avoidedItems.length > 0) {
    normalized.avoided_items = avoidedItems;
  }

  return normalized;
}

export function mergeProfileContext(
  current: FrontendProfileContext | null | undefined,
  update: FrontendProfileUpdate | null | undefined,
): FrontendProfileContext {
  const normalizedCurrent = normalizeProfileContext(current);
  const normalizedUpdate = normalizeProfileContext(update);

  return normalizeProfileContext({
    ...normalizedCurrent,
    ...normalizedUpdate,
  });
}

export function hasProfileContext(
  profileContext: FrontendProfileContext | null | undefined,
): boolean {
  const normalized = normalizeProfileContext(profileContext);
  const extensionFields = collectProfileExtensionFields(normalized);
  return (
    Boolean(normalized.presentation_profile) ||
    (normalized.fit_preferences?.length ?? 0) > 0 ||
    (normalized.silhouette_preferences?.length ?? 0) > 0 ||
    (normalized.comfort_preferences?.length ?? 0) > 0 ||
    (normalized.formality_preferences?.length ?? 0) > 0 ||
    (normalized.color_preferences?.length ?? 0) > 0 ||
    (normalized.color_avoidances?.length ?? 0) > 0 ||
    (normalized.preferred_items?.length ?? 0) > 0 ||
    (normalized.avoided_items?.length ?? 0) > 0 ||
    Object.keys(extensionFields).length > 0
  );
}

export function readStoredProfileContext(): FrontendProfileContext {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    const raw = window.localStorage.getItem(PROFILE_CONTEXT_STORAGE_KEY);
    if (!raw) {
      return {};
    }
    return normalizeProfileContext(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function writeStoredProfileContext(profileContext: FrontendProfileContext): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(
      PROFILE_CONTEXT_STORAGE_KEY,
      JSON.stringify(normalizeProfileContext(profileContext)),
    );
  } catch {
    // Ignore browser storage failures.
  }
}

export function buildProfileRequestEnvelope({
  profileContext,
  recentUpdate,
}: {
  profileContext?: FrontendProfileContext | null;
  recentUpdate?: FrontendProfileUpdate | null;
}): {
  profileContext?: FrontendProfileContext;
  metadata: Record<string, unknown>;
} {
  const effectiveProfile = mergeProfileContext(profileContext, recentUpdate);
  const metadata: Record<string, unknown> = {};

  if (hasProfileContext(effectiveProfile)) {
    metadata.session_profile_context = effectiveProfile;
  }

  const normalizedUpdate = normalizeProfileContext(recentUpdate);
  if (hasProfileContext(normalizedUpdate)) {
    metadata.profile_recent_updates = normalizedUpdate;
  }

  return {
    profileContext: hasProfileContext(effectiveProfile) ? effectiveProfile : undefined,
    metadata,
  };
}

export function extractProfileUpdateFromClarification({
  questionText,
  answerText,
}: {
  questionText: string | null | undefined;
  answerText: string | null | undefined;
}): FrontendProfileUpdate | null {
  const normalizedQuestion = normalizeText(questionText);
  const normalizedAnswer = normalizeText(answerText);

  if (!normalizedQuestion || !normalizedAnswer) {
    return null;
  }

  if (normalizedQuestion.includes("feminine") || normalizedQuestion.includes("masculine")) {
    const presentationProfile = matchPresentationProfileInText(normalizedAnswer);
    return presentationProfile ? { presentation_profile: presentationProfile } : null;
  }

  if (
    normalizedQuestion.includes("silhouette")
    || normalizedQuestion.includes("oversized")
    || normalizedQuestion.includes("fitted")
    || normalizedQuestion.includes("relaxed")
  ) {
    const fitPreferences = matchFitPreferencesInText(normalizedAnswer);
    if (fitPreferences.length > 0) {
      return { fit_preferences: fitPreferences };
    }

    const silhouettePreferences = matchSilhouettePreferencesInText(normalizedAnswer);
    return silhouettePreferences.length > 0
      ? { silhouette_preferences: silhouettePreferences }
      : null;
  }

  if (
    normalizedQuestion.includes("wearable")
    || normalizedQuestion.includes("comfortable")
    || normalizedQuestion.includes("expressive")
  ) {
    const comfortPreferences = matchComfortPreferencesInText(normalizedAnswer);
    return comfortPreferences.length > 0
      ? { comfort_preferences: comfortPreferences }
      : null;
  }

  if (
    normalizedQuestion.includes("casual")
    || normalizedQuestion.includes("formal")
    || normalizedQuestion.includes("refined")
    || normalizedQuestion.includes("smart casual")
  ) {
    const formalityPreferences = matchFormalityPreferencesInText(normalizedAnswer);
    return formalityPreferences.length > 0
      ? { formality_preferences: formalityPreferences }
      : null;
  }

  return null;
}

export function buildProfileClarificationSuggestions(
  locale: Locale,
  questionText: string | null | undefined,
): ClarificationSuggestion[] {
  const normalizedQuestion = normalizeText(questionText);
  if (!normalizedQuestion) {
    return [];
  }

  if (normalizedQuestion.includes("feminine") || normalizedQuestion.includes("masculine")) {
    return [
      suggestion(locale, "Feminine"),
      suggestion(locale, "Masculine"),
      suggestion(locale, "Androgynous"),
      suggestion(locale, "Universal"),
    ];
  }

  if (
    normalizedQuestion.includes("silhouette")
    || normalizedQuestion.includes("oversized")
    || normalizedQuestion.includes("fitted")
    || normalizedQuestion.includes("relaxed")
  ) {
    return [
      suggestion(locale, "Relaxed"),
      suggestion(locale, "Fitted"),
      suggestion(locale, "Oversized"),
    ];
  }

  if (
    normalizedQuestion.includes("wearable")
    || normalizedQuestion.includes("comfortable")
    || normalizedQuestion.includes("expressive")
  ) {
    return [
      suggestion(locale, "High comfort"),
      suggestion(locale, "Balanced"),
      suggestion(locale, "Style first"),
    ];
  }

  if (
    normalizedQuestion.includes("casual")
    || normalizedQuestion.includes("formal")
    || normalizedQuestion.includes("refined")
    || normalizedQuestion.includes("smart casual")
  ) {
    return [
      suggestion(locale, "Casual"),
      suggestion(locale, "Smart casual"),
      suggestion(locale, "Refined"),
      suggestion(locale, "Formal"),
    ];
  }

  return [];
}

function suggestion(locale: Locale, value: string): ClarificationSuggestion {
  if (locale === "ru") {
    if (value === "High comfort") {
      return { label: "High comfort", draft: "High comfort" };
    }
    if (value === "Style first") {
      return { label: "Style first", draft: "Style first" };
    }
  }

  return { label: value, draft: value };
}

function normalizePresentationProfile(value: unknown): FrontendPresentationProfile | null {
  const normalized = normalizeToken(value);
  const aliases: Record<string, FrontendPresentationProfile> = {
    feminine: "feminine",
    female: "feminine",
    woman: "feminine",
    "женственный": "feminine",
    masculine: "masculine",
    male: "masculine",
    man: "masculine",
    "мужественный": "masculine",
    androgynous: "androgynous",
    "андрогинный": "androgynous",
    neutral: "unisex",
    universal: "unisex",
    unisex: "unisex",
    "унисекс": "unisex",
  };
  const token = aliases[normalized] ?? normalized;
  return presentationProfileSet.has(token) ? (token as FrontendPresentationProfile) : null;
}

function matchPresentationProfileInText(
  value: string,
): FrontendPresentationProfile | null {
  if (containsAny(value, ["universal"])) {
    return "unisex";
  }
  if (containsAny(value, ["androgynous", "андрогин"])) {
    return "androgynous";
  }
  if (containsAny(value, ["unisex", "унисекс", "neutral", "нейтраль"])) {
    return "unisex";
  }
  if (containsAny(value, ["feminine", "female", "woman", "женствен"])) {
    return "feminine";
  }
  if (containsAny(value, ["masculine", "male", "man", "мужествен"])) {
    return "masculine";
  }
  return normalizePresentationProfile(value);
}

function matchFitPreferencesInText(value: string): FrontendFitPreference[] {
  const matches: FrontendFitPreference[] = [];
  if (containsAny(value, ["relaxed", "loose", "roomy", "расслаб", "свобод"])) {
    matches.push("relaxed");
  }
  if (containsAny(value, ["fitted", "tailored", "slim", "притал", "собран"])) {
    matches.push("fitted");
  }
  if (containsAny(value, ["oversized", "oversize", "оверсайз"])) {
    matches.push("oversized");
  }
  if (containsAny(value, ["balanced", "regular", "сбаланс"])) {
    matches.push("balanced");
  }
  return matches;
}

function matchSilhouettePreferencesInText(value: string): FrontendSilhouettePreference[] {
  const matches: FrontendSilhouettePreference[] = [];
  if (containsAny(value, ["soft", "мягк"])) {
    matches.push("soft");
  }
  if (containsAny(value, ["structured", "структур"])) {
    matches.push("structured");
  }
  if (containsAny(value, ["elongated", "вытянут"])) {
    matches.push("elongated");
  }
  if (containsAny(value, ["minimal", "минимал"])) {
    matches.push("minimal");
  }
  if (containsAny(value, ["layered", "многослой"])) {
    matches.push("layered");
  }
  if (containsAny(value, ["voluminous top", "voluminous_top"])) {
    matches.push("voluminous_top");
  }
  if (containsAny(value, ["balanced proportions", "balanced_proportions", "сбалансир"])) {
    matches.push("balanced_proportions");
  }
  return matches;
}

function matchComfortPreferencesInText(value: string): FrontendComfortPreference[] {
  const matches: FrontendComfortPreference[] = [];
  if (containsAny(value, ["high comfort", "comfortable", "comfort first", "комфорт"])) {
    matches.push("high_comfort");
  }
  if (containsAny(value, ["style first", "expressive", "statement", "выразит"])) {
    matches.push("style_first");
  }
  if (containsAny(value, ["balanced", "balance", "баланс"])) {
    matches.push("balanced");
  }
  return matches;
}

function matchFormalityPreferencesInText(value: string): FrontendFormalityPreference[] {
  const matches: FrontendFormalityPreference[] = [];
  if (containsAny(value, ["smart casual", "smart-casual", "смарт кэжуал"])) {
    matches.push("smart_casual");
  }
  if (containsAny(value, ["refined", "polished", "elevated", "собран"])) {
    matches.push("refined");
  }
  if (containsAny(value, ["formal", "dressy", "формал"])) {
    matches.push("formal");
  }
  if (containsAny(value, ["casual", "кэжуал", "повседнев"])) {
    matches.push("casual");
  }
  return matches;
}

function normalizeClosedSet<T extends string>(
  value: unknown,
  allowed: Set<string>,
  aliases: Record<string, string>,
  maxItems: number,
): T[] {
  const normalized: T[] = [];
  for (const token of collectTokens(value)) {
    const resolved = aliases[token] ?? token;
    if (!allowed.has(resolved) || normalized.includes(resolved as T)) {
      continue;
    }
    normalized.push(resolved as T);
    if (normalized.length >= maxItems) {
      break;
    }
  }
  return normalized;
}

function normalizeOpenTextSet(value: unknown, maxItems: number): string[] {
  const normalized: string[] = [];
  for (const token of collectTextTokens(value)) {
    if (normalized.includes(token)) {
      continue;
    }
    normalized.push(token);
    if (normalized.length >= maxItems) {
      break;
    }
  }
  return normalized;
}

function collectProfileExtensionFields(
  payload: Record<string, unknown>,
): FrontendProfileContext {
  const extensionFields: FrontendProfileContext = {};
  for (const [key, value] of Object.entries(payload)) {
    if (knownProfileContextKeys.has(key) || value == null) {
      continue;
    }
    if (Array.isArray(value)) {
      extensionFields[key] = [...value];
      continue;
    }
    if (isRecord(value)) {
      extensionFields[key] = { ...value };
      continue;
    }
    extensionFields[key] = value;
  }
  return extensionFields;
}

function collectTokens(value: unknown): string[] {
  if (value == null || typeof value === "boolean") {
    return [];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => collectTokens(item));
  }

  return normalizeListishValue(value)
    .map((part) => normalizeToken(part))
    .filter(Boolean);
}

function collectTextTokens(value: unknown): string[] {
  if (value == null || typeof value === "boolean") {
    return [];
  }

  if (Array.isArray(value)) {
    return value.flatMap((item) => collectTextTokens(item));
  }

  return normalizeListishValue(value)
    .map((part) => normalizeText(part))
    .filter(Boolean);
}

function normalizeListishValue(value: unknown): string[] {
  return String(value)
    .replace(/;/g, ",")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function normalizeToken(value: unknown): string {
  return normalizeText(value).replace(/-/g, "_").replace(/\s+/g, "_");
}

function normalizeText(value: unknown): string {
  return String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}

function containsAny(value: string, candidates: string[]): boolean {
  return candidates.some((candidate) => value.includes(candidate));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
