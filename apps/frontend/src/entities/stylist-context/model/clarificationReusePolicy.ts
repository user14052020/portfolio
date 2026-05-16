import type { FrontendScenarioContext } from "@/entities/stylist-context/model/types";

export function shouldReuseActiveStyleClarification({
  actionId,
  context,
}: {
  actionId: string;
  context: FrontendScenarioContext;
}) {
  return (
    actionId === "style_exploration" &&
    context.pendingClarification &&
    context.clarificationKind === "style_preference"
  );
}
