import {
  hasProfileContext,
  mergeProfileContext,
} from "@/entities/profile/model/profileContext";
import type {
  FrontendFitPreference,
  FrontendPresentationProfile,
  FrontendProfileContext,
  FrontendProfileUpdate,
} from "@/entities/profile/model/types";
import type { Locale } from "@/shared/api/types";

import type { FrontendScenarioContext } from "./types";

export type StructuredClarificationQuestionId =
  | "event_type"
  | "time_of_day"
  | "season"
  | "desired_impression"
  | "presentation_profile"
  | "fit_preference"
  | "style_presentation_profile"
  | "style_wearability"
  | "style_silhouette"
  | "style_palette"
  | "style_mood";

export type StructuredClarificationOption = {
  id: string;
  label: string;
  draft: string;
  profileUpdate?: FrontendProfileUpdate | null;
  metadata?: Record<string, unknown>;
};

export type StructuredClarificationQuestion = {
  id: StructuredClarificationQuestionId;
  title: string;
  options: StructuredClarificationOption[];
};

export type StructuredClarificationForm = {
  kind: "occasion_batch" | "style_exploration_batch";
  title: string;
  submitLabel: string;
  questions: StructuredClarificationQuestion[];
};

export type StructuredClarificationAnswers = Partial<
  Record<StructuredClarificationQuestionId, string>
>;

export type StructuredClarificationSubmission = {
  draftMessage: string;
  profileRecentUpdate: FrontendProfileUpdate | null;
  metadata?: Record<string, unknown>;
};

export function buildStructuredClarificationForm({
  locale,
  scenarioContext,
  profileContext: _profileContext,
}: {
  locale: Locale;
  scenarioContext: FrontendScenarioContext;
  profileContext: FrontendProfileContext | null | undefined;
}): StructuredClarificationForm | null {
  if (!scenarioContext.pendingClarification) {
    return null;
  }

  void _profileContext;

  if (scenarioContext.activeMode === "style_exploration") {
    return buildStyleExplorationClarificationForm(locale);
  }

  if (scenarioContext.activeMode !== "occasion_outfit") {
    return null;
  }

  const questions: StructuredClarificationQuestion[] = [];

  questions.push(
    {
      id: "event_type",
      title: locale === "ru" ? "Что это за событие?" : "What kind of event is it?",
      options: buildEventTypeOptions(locale),
    },
    {
      id: "time_of_day",
      title: locale === "ru" ? "Когда это происходит?" : "What time of day is it?",
      options: buildTimeOfDayOptions(locale),
    },
    {
      id: "season",
      title: locale === "ru" ? "Какой сейчас сезон?" : "What season is it?",
      options: buildSeasonOptions(locale),
    },
    {
      id: "desired_impression",
      title:
        locale === "ru"
          ? "Какое впечатление вы хотите произвести?"
          : "What impression do you want to create?",
      options: buildDesiredImpressionOptions(locale),
    },
    {
      id: "presentation_profile",
      title: locale === "ru" ? "Для кого собираем образ?" : "Who is the look for?",
      options: buildPresentationProfileOptions(locale),
    },
    {
      id: "fit_preference",
      title: locale === "ru" ? "Какой силуэт вам ближе?" : "Which silhouette feels right?",
      options: buildFitPreferenceOptions(locale),
    },
  );

  if (questions.length === 0) {
    return null;
  }

  return {
    kind: "occasion_batch",
    title:
      locale === "ru"
        ? "Можно выбрать всё сразу, и я соберу ответ одним сообщением"
        : "You can choose everything at once and I will turn it into one reply",
    submitLabel: locale === "ru" ? "Собрать ответ" : "Build the reply",
    questions,
  };
}

export function buildStructuredClarificationSubmission({
  form,
  answers,
}: {
  form: StructuredClarificationForm;
  answers: StructuredClarificationAnswers;
}): StructuredClarificationSubmission | null {
  const selectedOptions = form.questions.map((question) => {
    const selectedOptionId = answers[question.id];
    if (!selectedOptionId) {
      return null;
    }

    return question.options.find((option) => option.id === selectedOptionId) ?? null;
  });

  if (selectedOptions.some((option) => option == null)) {
    return null;
  }

  const draftParts: string[] = [];
  let profileRecentUpdate: FrontendProfileUpdate | null = null;
  let metadata: Record<string, unknown> | null = null;

  for (const option of selectedOptions) {
    if (!option) {
      continue;
    }

    if (option.draft.trim()) {
      draftParts.push(option.draft.trim());
    }

    if (option.profileUpdate) {
      profileRecentUpdate = mergeProfileContext(profileRecentUpdate, option.profileUpdate);
    }

    if (option.metadata) {
      metadata = mergeMetadata(metadata, option.metadata);
    }
  }

  return {
    draftMessage: draftParts.join(" "),
    profileRecentUpdate:
      profileRecentUpdate && hasProfileContext(profileRecentUpdate)
        ? profileRecentUpdate
        : null,
    metadata: metadata ?? undefined,
  };
}

function buildStyleExplorationClarificationForm(locale: Locale): StructuredClarificationForm {
  return {
    kind: "style_exploration_batch",
    title:
      locale === "ru"
        ? "Выберите, в какую сторону увести следующий стиль"
        : "Choose the direction for the next style",
    submitLabel: locale === "ru" ? "Подобрать стиль" : "Choose the style",
    questions: [
      {
        id: "style_presentation_profile",
        title: locale === "ru" ? "Для кого собираем стиль?" : "Who is the style for?",
        options: buildStylePresentationProfileOptions(locale),
      },
      {
        id: "style_wearability",
        title: locale === "ru" ? "Насколько носибельным должен быть стиль?" : "How wearable should it feel?",
        options: buildStyleWearabilityOptions(locale),
      },
      {
        id: "style_silhouette",
        title: locale === "ru" ? "Какой силуэт ближе?" : "Which silhouette should guide it?",
        options: buildStyleSilhouetteOptions(locale),
      },
      {
        id: "style_palette",
        title: locale === "ru" ? "Какая палитра сейчас нужна?" : "What palette should it lean into?",
        options: buildStylePaletteOptions(locale),
      },
      {
        id: "style_mood",
        title: locale === "ru" ? "Какое настроение выбрать?" : "What mood should lead?",
        options: buildStyleMoodOptions(locale),
      },
    ],
  };
}

function mergeMetadata(
  current: Record<string, unknown> | null,
  update: Record<string, unknown>,
): Record<string, unknown> {
  const result: Record<string, unknown> = { ...(current ?? {}) };
  for (const [key, value] of Object.entries(update)) {
    const existing = result[key];
    if (isRecord(existing) && isRecord(value)) {
      result[key] = mergeMetadata(existing, value);
      continue;
    }
    result[key] = value;
  }
  return result;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function buildEventTypeOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      option("wedding", "Свадьба", "Это свадьба."),
      option("date", "Свидание", "Это свидание."),
      option("dinner", "Ужин", "Это ужин."),
      option("theater", "Театр", "Это театр."),
      option("party", "Вечеринка", "Это вечеринка."),
      option("exhibition", "Выставка", "Это выставка."),
      option("conference", "Конференция", "Это конференция."),
      option("birthday", "День рождения", "Это день рождения."),
    ];
  }

  return [
    option("wedding", "Wedding", "It is a wedding."),
    option("date", "Date", "It is a date."),
    option("dinner", "Dinner", "It is a dinner."),
    option("theater", "Theater", "It is a theater night."),
    option("party", "Party", "It is a party."),
    option("exhibition", "Exhibition", "It is an exhibition."),
    option("conference", "Conference", "It is a conference."),
    option("birthday", "Birthday", "It is a birthday."),
  ];
}

function buildTimeOfDayOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      option("morning", "Утром", "Это утром."),
      option("day", "Днём", "Это днём."),
      option("evening", "Вечером", "Это вечером."),
      option("night", "Ночью", "Это ночью."),
    ];
  }

  return [
    option("morning", "Morning", "It happens in the morning."),
    option("day", "Daytime", "It happens in the daytime."),
    option("evening", "Evening", "It happens in the evening."),
    option("night", "Night", "It happens at night."),
  ];
}

function buildSeasonOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      option("spring", "Весна", "Сейчас весна."),
      option("summer", "Лето", "Сейчас лето."),
      option("autumn", "Осень", "Сейчас осень."),
      option("winter", "Зима", "Сейчас зима."),
    ];
  }

  return [
    option("spring", "Spring", "It is spring now."),
    option("summer", "Summer", "It is summer now."),
    option("autumn", "Autumn", "It is autumn now."),
    option("winter", "Winter", "It is winter now."),
  ];
}

function buildDesiredImpressionOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      option("elegant", "Элегантно", "Хочу выглядеть элегантно."),
      option("confident", "Уверенно", "Хочу выглядеть уверенно."),
      option("relaxed", "Расслабленно", "Хочу выглядеть расслабленно."),
      option("bold", "Смело", "Хочу выглядеть смело."),
      option("romantic", "Романтично", "Хочу выглядеть романтично."),
    ];
  }

  return [
    option("elegant", "Elegant", "I want to look elegant."),
    option("confident", "Confident", "I want to look confident."),
    option("relaxed", "Relaxed", "I want to look relaxed."),
    option("bold", "Bold", "I want to look bold."),
    option("romantic", "Romantic", "I want to look romantic."),
  ];
}

function buildPresentationProfileOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      presentationOption("feminine", "Женщина", "Собираем женский образ."),
      presentationOption("masculine", "Мужчина", "Собираем мужской образ."),
      presentationOption("androgynous", "Андрогинно", "Хочу более андрогинный образ."),
      presentationOption("unisex", "Универсально", "Подойдёт более универсальный образ."),
    ];
  }

  return [
    presentationOption("feminine", "Woman", "Build the look on a feminine line."),
    presentationOption("masculine", "Man", "Build the look on a masculine line."),
    presentationOption("androgynous", "Androgynous", "I want a more androgynous line."),
    presentationOption("unisex", "Universal", "A more universal line works best."),
  ];
}

function buildFitPreferenceOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      fitOption("relaxed", "Свободный", "Предпочитаю свободный силуэт."),
      fitOption("fitted", "Приталенный", "Предпочитаю приталенный силуэт."),
      fitOption("oversized", "Оверсайз", "Предпочитаю силуэт оверсайз."),
      fitOption("balanced", "Сбалансированный", "Предпочитаю сбалансированный силуэт."),
    ];
  }

  return [
    fitOption("relaxed", "Relaxed", "I prefer a relaxed silhouette."),
    fitOption("fitted", "Fitted", "I prefer a fitted silhouette."),
    fitOption("oversized", "Oversized", "I prefer an oversized silhouette."),
    fitOption("balanced", "Balanced", "I prefer a balanced silhouette."),
  ];
}

function buildStylePresentationProfileOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      stylePresentationOption("feminine", "Женский", "Собираем женский стиль."),
      stylePresentationOption("masculine", "Мужской", "Собираем мужской стиль."),
      stylePresentationOption("androgynous", "Андрогинный", "Собираем андрогинный стиль."),
      stylePresentationOption("unisex", "Универсальный", "Собираем универсальный стиль."),
    ];
  }

  return [
    stylePresentationOption("feminine", "Feminine", "Build a feminine style direction."),
    stylePresentationOption("masculine", "Masculine", "Build a masculine style direction."),
    stylePresentationOption("androgynous", "Androgynous", "Build an androgynous style direction."),
    stylePresentationOption("unisex", "Universal", "Build a universal style direction."),
  ];
}

function buildStyleWearabilityOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      stylePreferenceOption("wearability", "wearable", "Очень носибельно", "Хочу очень носибельный стиль."),
      stylePreferenceOption("wearability", "balanced", "Баланс", "Хочу баланс носибельности и выразительности."),
      stylePreferenceOption("wearability", "expressive", "Выразительно", "Хочу более выразительный стиль."),
    ];
  }

  return [
    stylePreferenceOption("wearability", "wearable", "Highly wearable", "Keep it highly wearable."),
    stylePreferenceOption("wearability", "balanced", "Balanced", "Balance wearability and expression."),
    stylePreferenceOption("wearability", "expressive", "More expressive", "Make the style more expressive."),
  ];
}

function buildStyleSilhouetteOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      stylePreferenceOption("silhouette", "relaxed", "Расслабленный", "Ближе расслабленный силуэт."),
      stylePreferenceOption("silhouette", "tailored", "Собранный", "Ближе собранный и структурный силуэт."),
      stylePreferenceOption("silhouette", "oversized", "Оверсайз", "Ближе объёмный силуэт."),
      stylePreferenceOption("silhouette", "fluid", "Мягкий", "Ближе мягкий и пластичный силуэт."),
    ];
  }

  return [
    stylePreferenceOption("silhouette", "relaxed", "Relaxed", "A relaxed silhouette feels right."),
    stylePreferenceOption("silhouette", "tailored", "Tailored", "A tailored structured silhouette feels right."),
    stylePreferenceOption("silhouette", "oversized", "Oversized", "An oversized silhouette feels right."),
    stylePreferenceOption("silhouette", "fluid", "Fluid", "A soft fluid silhouette feels right."),
  ];
}

function buildStylePaletteOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      stylePreferenceOption("palette", "neutral", "Нейтральная", "Нужна нейтральная палитра."),
      stylePreferenceOption("palette", "dark", "Тёмная", "Нужна более тёмная палитра."),
      stylePreferenceOption("palette", "colorful", "Цветная", "Хочу больше цвета."),
      stylePreferenceOption("palette", "soft", "Мягкая", "Нужна мягкая светлая палитра."),
    ];
  }

  return [
    stylePreferenceOption("palette", "neutral", "Neutral", "Use a neutral palette."),
    stylePreferenceOption("palette", "dark", "Dark", "Use a darker palette."),
    stylePreferenceOption("palette", "colorful", "Color", "Bring in more color."),
    stylePreferenceOption("palette", "soft", "Soft", "Use a soft light palette."),
  ];
}

function buildStyleMoodOptions(locale: Locale): StructuredClarificationOption[] {
  if (locale === "ru") {
    return [
      stylePreferenceOption("mood", "minimal", "Минимализм", "Настроение ближе к минимализму."),
      stylePreferenceOption("mood", "romantic", "Романтика", "Настроение ближе к романтичности."),
      stylePreferenceOption("mood", "street", "Улица", "Настроение ближе к streetwear или workwear."),
      stylePreferenceOption("mood", "classic", "Классика", "Настроение ближе к современной классике."),
      stylePreferenceOption("mood", "artful", "Арт", "Настроение ближе к арт-направлению."),
    ];
  }

  return [
    stylePreferenceOption("mood", "minimal", "Minimal", "Keep the mood minimal."),
    stylePreferenceOption("mood", "romantic", "Romantic", "Lean into a romantic mood."),
    stylePreferenceOption("mood", "street", "Street", "Lean toward streetwear or workwear."),
    stylePreferenceOption("mood", "classic", "Classic", "Lean toward modern classic dressing."),
    stylePreferenceOption("mood", "artful", "Artful", "Lean toward an artful direction."),
  ];
}

function stylePreferenceOption(
  key: "presentation_profile" | "wearability" | "silhouette" | "palette" | "mood",
  id: string,
  label: string,
  draft: string,
): StructuredClarificationOption {
  return {
    id,
    label,
    draft,
    metadata: {
      style_exploration_preferences: {
        [key]: id,
      },
    },
  };
}

function stylePresentationOption(
  id: FrontendPresentationProfile,
  label: string,
  draft: string,
): StructuredClarificationOption {
  return {
    ...stylePreferenceOption("presentation_profile", id, label, draft),
    profileUpdate: {
      presentation_profile: id,
    },
  };
}

function fitOption(
  id: FrontendFitPreference,
  label: string,
  draft: string,
): StructuredClarificationOption {
  return {
    id,
    label,
    draft,
    profileUpdate: {
      fit_preferences: [id],
    },
  };
}

function presentationOption(
  id: FrontendPresentationProfile,
  label: string,
  draft: string,
): StructuredClarificationOption {
  return {
    id,
    label,
    draft,
    profileUpdate: {
      presentation_profile: id,
    },
  };
}

function option(id: string, label: string, draft: string): StructuredClarificationOption {
  return {
    id,
    label,
    draft,
  };
}
