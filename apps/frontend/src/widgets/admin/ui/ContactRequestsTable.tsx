"use client";

import { Select } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getContactRequests, updateContactRequest } from "@/shared/api/client";
import type { ContactRequest } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

export function ContactRequestsTable() {
  const { tokens } = useAdminAuth();
  const [items, setItems] = useState<ContactRequest[]>([]);

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }
    getContactRequests(tokens.access_token)
      .then(setItems)
      .catch(() => setItems([]));
  }, [tokens?.access_token]);

  return (
    <WindowFrame title="Contact requests" subtitle="Inbox">
      <div className="space-y-3">
        {items.map((item) => (
          <div key={item.id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
            <div className="grid gap-4 md:grid-cols-[1fr_200px] md:items-center">
              <div>
                <p className="font-medium text-slate-900">
                  {item.name} · {item.email}
                </p>
                <p className="text-sm leading-7 text-slate-600">{item.message}</p>
              </div>
              <Select
                value={item.status}
                data={[
                  { label: "New", value: "new" },
                  { label: "In progress", value: "in_progress" },
                  { label: "Closed", value: "closed" }
                ]}
                onChange={async (value) => {
                  if (!value || !tokens?.access_token) {
                    return;
                  }
                  const updated = await updateContactRequest(item.id, { status: value as ContactRequest["status"] }, tokens.access_token);
                  setItems((current) => current.map((entry) => (entry.id === item.id ? updated : entry)));
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </WindowFrame>
  );
}
