import type { ReactNode, UIEventHandler } from "react";
import { forwardRef } from "react";

import { cn } from "@/shared/lib/cn";

export const ChatConversationSurface = forwardRef<
  HTMLDivElement,
  {
    children: ReactNode;
    onScroll: UIEventHandler<HTMLDivElement>;
    className?: string;
  }
>(function ChatConversationSurface({ children, onScroll, className }, ref) {
  return (
    <div
      ref={ref}
      className={cn(
        "premium-scrollbar h-[520px] overflow-y-auto bg-[radial-gradient(circle_at_16%_0%,rgba(239,237,255,0.48),transparent_20rem),linear-gradient(180deg,#fffdfa_0%,#f7f5f0_100%)] px-4 py-5 md:px-6 md:py-6",
        className,
      )}
      onScroll={onScroll}
    >
      {children}
    </div>
  );
});
