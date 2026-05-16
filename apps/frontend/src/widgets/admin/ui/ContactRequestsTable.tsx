"use client";

import { Select } from "@mantine/core";
import { useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getContactRequests, updateContactRequest } from "@/shared/api/client";
import type { ContactRequest } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

type InboxStatus = "idle" | "loading" | "ready" | "error";

const CONTACT_STATUS_OPTIONS: Array<{ label: string; value: ContactRequest["status"] }> = [
  { label: "New", value: "new" },
  { label: "In progress", value: "in_progress" },
  { label: "Closed", value: "closed" },
];

function formatDateTime(value: string) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function statusTone(status: ContactRequest["status"]): "accent" | "warning" | "success" {
  if (status === "closed") {
    return "success";
  }
  if (status === "in_progress") {
    return "warning";
  }
  return "accent";
}

export function ContactRequestsTable() {
  const { tokens } = useAdminAuth();
  const [items, setItems] = useState<ContactRequest[]>([]);
  const [status, setStatus] = useState<InboxStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  useEffect(() => {
    if (!tokens?.access_token) {
      setStatus("idle");
      return;
    }

    let cancelled = false;
    setStatus("loading");

    getContactRequests(tokens.access_token)
      .then((nextItems) => {
        if (cancelled) {
          return;
        }
        setItems(nextItems);
        setError(null);
        setStatus("ready");
      })
      .catch((nextError) => {
        if (cancelled) {
          return;
        }
        setItems([]);
        setError(nextError instanceof Error ? nextError.message : "Failed to load contact requests");
        setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [tokens?.access_token]);

  async function handleStatusChange(item: ContactRequest, value: string | null) {
    if (!value || !tokens?.access_token) {
      return;
    }
    setSavingId(item.id);
    try {
      const updated = await updateContactRequest(
        item.id,
        { status: value as ContactRequest["status"] },
        tokens.access_token,
      );
      setItems((current) => current.map((entry) => (entry.id === item.id ? updated : entry)));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to update contact request");
    } finally {
      setSavingId(null);
    }
  }

  const newCount = items.filter((item) => item.status === "new").length;
  const inProgressCount = items.filter((item) => item.status === "in_progress").length;
  const closedCount = items.filter((item) => item.status === "closed").length;

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <ContactInboxHeader statusLabel="auth required" />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to review and triage contact requests.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard
      variant="elevated"
      header={<ContactInboxHeader statusLabel={status === "loading" ? "loading" : "live inbox"} />}
    >
      <div className="space-y-5">
        <div className="grid gap-3 md:grid-cols-3">
          <InboxMetric label="New" value={newCount} tone="accent" />
          <InboxMetric label="In progress" value={inProgressCount} tone="warning" />
          <InboxMetric label="Closed" value={closedCount} tone="success" />
        </div>

        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="space-y-3">
          {items.map((item) => (
            <ContactRequestCard
              key={item.id}
              item={item}
              isSaving={savingId === item.id}
              onStatusChange={(value) => void handleStatusChange(item, value)}
            />
          ))}
          {items.length === 0 ? (
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5 text-sm text-[var(--text-secondary)]">
              {status === "loading" ? "Loading contact requests..." : "No contact requests yet."}
            </div>
          ) : null}
        </div>
      </div>
    </SurfaceCard>
  );
}

function ContactInboxHeader({ statusLabel }: { statusLabel: string }) {
  return (
    <SectionHeader
      eyebrow="Admin inbox"
      title="Contact requests"
      description="Review inbound messages, keep triage status visible, and close handled requests without leaving the control room."
      action={<PillBadge tone="dark">{statusLabel}</PillBadge>}
    />
  );
}

function InboxMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "accent" | "warning" | "success";
}) {
  return (
    <div className="rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">{label}</p>
        <PillBadge tone={tone} size="sm">
          status
        </PillBadge>
      </div>
      <p className="mt-3 font-display text-4xl text-[var(--text-primary)]">{value}</p>
    </div>
  );
}

function ContactRequestCard({
  item,
  isSaving,
  onStatusChange,
}: {
  item: ContactRequest;
  isSaving: boolean;
  onStatusChange: (value: string | null) => void;
}) {
  return (
    <article className="rounded-[26px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_220px] lg:items-start">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <PillBadge tone={statusTone(item.status)} size="sm">
              {item.status.replace("_", " ")}
            </PillBadge>
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
              {formatDateTime(item.created_at)}
            </span>
          </div>
          <div>
            <p className="font-semibold text-[var(--text-primary)]">{item.name}</p>
            <p className="mt-1 break-all text-sm text-[var(--text-secondary)]">{item.email}</p>
          </div>
          <p className="text-sm leading-7 text-[var(--text-secondary)]">{item.message}</p>
          {item.source_page ? (
            <p className="break-all text-xs text-[var(--text-muted)]">Source: {item.source_page}</p>
          ) : null}
        </div>

        <Select
          label={isSaving ? "Saving..." : "Status"}
          value={item.status}
          data={CONTACT_STATUS_OPTIONS}
          disabled={isSaving}
          onChange={onStatusChange}
        />
      </div>
    </article>
  );
}
