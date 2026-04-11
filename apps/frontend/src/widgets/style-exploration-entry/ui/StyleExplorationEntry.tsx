import type { CommandName } from "@/entities/command/model/types";
import type { Locale } from "@/shared/api/types";
import { QuickActionsPanel } from "@/widgets/quick-actions/ui/QuickActionsPanel";

export function StyleExplorationEntry({
  locale,
  disabled,
  activeCommandName,
  onAction,
}: {
  locale: Locale;
  disabled: boolean;
  activeCommandName: CommandName | null;
  onAction: (actionId: CommandName) => void;
}) {
  return (
    <QuickActionsPanel
      locale={locale}
      disabled={disabled}
      activeCommandName={activeCommandName}
      onAction={onAction}
    />
  );
}
