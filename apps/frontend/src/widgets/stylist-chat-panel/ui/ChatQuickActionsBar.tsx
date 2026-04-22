import type { QuickActionDefinition } from "@/features/run-chat-command/model/runChatCommand";
import type { Locale } from "@/shared/api/types";
import { SoftButton } from "@/shared/ui/SoftButton";

export function ChatQuickActionsBar({
  quickActions,
  locale,
  disabled,
  disabledTitle,
  canShowVisualizationCta,
  visualizationCtaText,
  isVisualizationCtaDisabled,
  onRunQuickAction,
  onRequestVisualization,
}: {
  quickActions: QuickActionDefinition[];
  locale: Locale;
  disabled: boolean;
  disabledTitle?: string | null;
  canShowVisualizationCta: boolean;
  visualizationCtaText?: string | null;
  isVisualizationCtaDisabled: boolean;
  onRunQuickAction: (id: QuickActionDefinition["id"]) => void;
  onRequestVisualization: () => void;
}) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {quickActions.map((action) => (
          <SoftButton
            key={action.id}
            onClick={() => onRunQuickAction(action.id)}
            disabled={disabled}
            title={disabledTitle ?? undefined}
            tone="subtle"
            shape="pill"
          >
            {action.label}
          </SoftButton>
        ))}
      </div>

      {canShowVisualizationCta ? (
        <SoftButton
          onClick={onRequestVisualization}
          disabled={isVisualizationCtaDisabled}
          title={disabledTitle ?? undefined}
          tone="accent"
          shape="surface"
          fullWidth
          align="left"
          className="justify-between font-semibold"
        >
          {visualizationCtaText ?? (locale === "ru" ? "Собрать flat lay референс?" : "Build a flat lay reference?")}
        </SoftButton>
      ) : null}
    </div>
  );
}
