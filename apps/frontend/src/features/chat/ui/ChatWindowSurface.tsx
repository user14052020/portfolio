"use client";

import { StylistChatPanel } from "@/widgets/stylist-chat-panel/ui/StylistChatPanel";
import type { SiteSettings } from "@/shared/api/types";

export function ChatWindowSurface({ settings }: { settings: SiteSettings }) {
  return <StylistChatPanel settings={settings} />;
}
