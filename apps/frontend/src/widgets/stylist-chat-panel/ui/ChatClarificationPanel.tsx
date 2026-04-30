import { buildProfileClarificationSuggestions } from "@/entities/profile/model/profileContext";
import type { Locale } from "@/shared/api/types";
import { SoftButton } from "@/shared/ui/SoftButton";

export function ChatClarificationPanel({
  locale,
  text,
  onSuggestionSelect,
}: {
  locale: Locale;
  text: string;
  onSuggestionSelect?: (value: string) => void;
}) {
  const suggestions = buildProfileClarificationSuggestions(locale, text);

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion) => (
        <SoftButton
          key={suggestion.label}
          tone="accent"
          shape="compact"
          onClick={() => onSuggestionSelect?.(suggestion.draft)}
        >
          {suggestion.label}
        </SoftButton>
      ))}
    </div>
  );
}
