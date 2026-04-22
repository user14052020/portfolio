import { Suspense } from "react";

import { ChatSessionsTable } from "@/widgets/admin/ui/ChatSessionsTable";

export default function AdminChatsPage() {
  return (
    <Suspense fallback={<div className="text-sm text-[var(--text-secondary)]">Loading chat audit...</div>}>
      <ChatSessionsTable />
    </Suspense>
  );
}
