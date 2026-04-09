"use client";

import type { CommandName } from "@/entities/command/model/types";
import { getQuickActionDefinitions } from "@/features/run-chat-command/model/runChatCommand";
import type { Locale } from "@/shared/api/types";

function QuickActionIcon({
  kind,
}: {
  kind: "pair" | "style" | "occasion";
}) {
  if (kind === "pair") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M8 6c0-1.1.9-2 2-2h4c1.1 0 2 .9 2 2" />
        <path d="M12 8v2" />
        <path d="M6 9.5 12 14l6-4.5" />
        <path d="M6 9.5V18a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9.5" />
      </svg>
    );
  }

  if (kind === "style") {
    return (
      <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3l1.7 4.3L18 9l-4.3 1.7L12 15l-1.7-4.3L6 9l4.3-1.7L12 3Z" />
        <path d="M18.5 15.5 19.4 18l2.6.9-2.6.9-.9 2.6-.9-2.6-2.6-.9 2.6-.9.9-2.5Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8">
      <rect x="4" y="5" width="16" height="15" rx="2" />
      <path d="M8 3v4M16 3v4M4 10h16" />
      <path d="M8 14h3M13 14h3M8 17h3" />
    </svg>
  );
}

function getQuickActionButtonClass(isActive = false) {
  return isActive
    ? "inline-flex items-center gap-2 border border-slate-900 bg-slate-900 px-3 py-2 text-sm text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400"
    : "inline-flex items-center gap-2 border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 transition hover:border-slate-300 hover:bg-white disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400";
}

export function QuickActionsPanel({
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
  const actions = getQuickActionDefinitions(locale);

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => (
        <button
          key={action.id}
          type="button"
          disabled={disabled}
          onClick={() => onAction(action.id)}
          className={getQuickActionButtonClass(activeCommandName === action.id)}
        >
          <QuickActionIcon kind={action.kind} />
          <span>{action.label}</span>
        </button>
      ))}
    </div>
  );
}
