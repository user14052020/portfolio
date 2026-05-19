export type FrontendComfortPreference = "balanced" | "comfort_first" | "statement";
export type FrontendFitPreference = "regular" | "relaxed" | "tailored";
export type FrontendFormalityPreference = "casual" | "smart_casual" | "formal";
export type FrontendSilhouettePreference = "straight" | "soft_volume" | "structured";
export type FrontendPresentationProfileId =
  | "style_exploration"
  | "occasion_outfit"
  | "garment_matching";

export type FrontendProfileOption<Value extends string = string> = {
  value: Value;
  label_ru: string;
  label_en: string;
};

export type FrontendPresentationProfile = FrontendProfileOption<FrontendPresentationProfileId> & {
  preferredVisualizationType: string;
};

export interface PresentationProfile {
  preferredVisualizationType?: string | null;
  comfortPreference?: FrontendComfortPreference | string | null;
  fitPreference?: FrontendFitPreference | string | null;
  formalityPreference?: FrontendFormalityPreference | string | null;
  silhouettePreference?: FrontendSilhouettePreference | string | null;
  presentationProfile?: FrontendPresentationProfileId | string | null;
}

export const FRONTEND_COMFORT_PREFERENCES: FrontendProfileOption<FrontendComfortPreference>[] = [
  {
    value: "balanced",
    label_ru: "Баланс комфорта и выразительности",
    label_en: "Balanced comfort and expression",
  },
  {
    value: "comfort_first",
    label_ru: "Максимальный комфорт",
    label_en: "Comfort first",
  },
  {
    value: "statement",
    label_ru: "Можно смелее",
    label_en: "More expressive",
  },
];

export const FRONTEND_FIT_PREFERENCES: FrontendProfileOption<FrontendFitPreference>[] = [
  {
    value: "regular",
    label_ru: "Обычная посадка",
    label_en: "Regular fit",
  },
  {
    value: "relaxed",
    label_ru: "Свободная посадка",
    label_en: "Relaxed fit",
  },
  {
    value: "tailored",
    label_ru: "Более собранный силуэт",
    label_en: "Tailored silhouette",
  },
];

export const FRONTEND_FORMALITY_PREFERENCES: FrontendProfileOption<FrontendFormalityPreference>[] = [
  {
    value: "casual",
    label_ru: "Повседневно",
    label_en: "Casual",
  },
  {
    value: "smart_casual",
    label_ru: "Smart casual",
    label_en: "Smart casual",
  },
  {
    value: "formal",
    label_ru: "Формально",
    label_en: "Formal",
  },
];

export const FRONTEND_SILHOUETTE_PREFERENCES: FrontendProfileOption<FrontendSilhouettePreference>[] = [
  {
    value: "straight",
    label_ru: "Прямой силуэт",
    label_en: "Straight silhouette",
  },
  {
    value: "soft_volume",
    label_ru: "Мягкий объем",
    label_en: "Soft volume",
  },
  {
    value: "structured",
    label_ru: "Структурный силуэт",
    label_en: "Structured silhouette",
  },
];

export const FRONTEND_PRESENTATION_PROFILES: FrontendPresentationProfile[] = [
  {
    value: "style_exploration",
    label_ru: "Подбор стиля",
    label_en: "Style exploration",
    preferredVisualizationType: "style_exploration",
  },
  {
    value: "occasion_outfit",
    label_ru: "Образ под повод",
    label_en: "Occasion outfit",
    preferredVisualizationType: "occasion_outfit",
  },
  {
    value: "garment_matching",
    label_ru: "Собрать образ вокруг вещи",
    label_en: "Match an anchor garment",
    preferredVisualizationType: "garment_matching",
  },
];
