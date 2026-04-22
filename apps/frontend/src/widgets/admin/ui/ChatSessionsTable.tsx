"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { getAdminChatSessionDetails, getAdminChatSessions } from "@/shared/api/client";
import type { AdminChatSessionDetails, AdminChatSessionSummary } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { ChatSessionDetailsPanel } from "@/widgets/admin/ui/ChatSessionDetailsPanel";

const PAGE_LIMIT = 30;

function formatDate(value?: string | null) {
  if (!value) {
    return "n/a";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function shortId(sessionId: string) {
  if (sessionId.length <= 18) {
    return sessionId;
  }
  return `${sessionId.slice(0, 10)}...${sessionId.slice(-6)}`;
}

export function ChatSessionsTable() {
  const { tokens } = useAdminAuth();
  const searchParams = useSearchParams();
  const sessionFromQuery = searchParams.get("session");
  const [sessions, setSessions] = useState<AdminChatSessionSummary[]>([]);
  const [details, setDetails] = useState<AdminChatSessionDetails | null>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDetails(sessionId: string) {
    if (!tokens?.access_token) {
      return;
    }

    setIsLoadingDetails(true);
    setError(null);
    try {
      const nextDetails = await getAdminChatSessionDetails(sessionId, tokens.access_token);
      setDetails(nextDetails);
      setSelectedSessionId(sessionId);
      setError(null);
    } catch (nextError) {
      setDetails(null);
      setError(nextError instanceof Error ? nextError.message : "Failed to load chat session details");
    } finally {
      setIsLoadingDetails(false);
    }
  }

  async function loadSessions(nextQuery = appliedQuery, preferredSessionId?: string | null) {
    if (!tokens?.access_token) {
      return;
    }

    setIsLoadingSessions(true);
    setError(null);
    try {
      const page = await getAdminChatSessions(tokens.access_token, {
        limit: PAGE_LIMIT,
        q: nextQuery || undefined,
      });
      setSessions(page.items);
      setTotal(page.total);

      const selectedCandidate = preferredSessionId || selectedSessionId;
      const selectedStillVisible = page.items.some((item) => item.session_id === selectedCandidate);
      const nextSelected = selectedStillVisible
        ? selectedCandidate
        : (preferredSessionId || page.items[0]?.session_id) ?? null;
      if (nextSelected) {
        await loadDetails(nextSelected);
      } else {
        setSelectedSessionId(null);
        setDetails(null);
      }
    } catch (nextError) {
      setSessions([]);
      setTotal(0);
      setDetails(null);
      setSelectedSessionId(null);
      setError(nextError instanceof Error ? nextError.message : "Failed to load chat sessions");
    } finally {
      setIsLoadingSessions(false);
    }
  }

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }
    loadSessions("", sessionFromQuery);
  }, [tokens?.access_token, sessionFromQuery]);

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextQuery = query.trim();
    setAppliedQuery(nextQuery);
    loadSessions(nextQuery);
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        eyebrow="Admin audit"
        title="Chat sessions"
        description="Inspect stylist conversations as operational sessions: message timeline, generation jobs, IP, user-agent and runtime state."
        action={
          <form onSubmit={handleSearch} className="flex min-w-[280px] gap-2">
            <input
              value={query}
              onChange={(event) => setQuery(event.currentTarget.value)}
              placeholder="Search session, IP, mode..."
              className="min-w-0 flex-1 rounded-[var(--radius-pill)] border border-[var(--border-soft)] bg-white/80 px-4 py-2.5 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--border-strong)]"
            />
            <SoftButton type="submit" tone="dark">
              Search
            </SoftButton>
          </form>
        }
      />

      {error ? (
        <SurfaceCard variant="soft" padding="sm" className="border-rose-200 bg-rose-50/80">
          <p className="text-sm text-rose-700">{error}</p>
        </SurfaceCard>
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(380px,0.95fr)]">
        <SurfaceCard
          variant="tinted"
          className="min-h-[520px]"
          header={
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--text-muted)]">
                  Session index
                </p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  {total} total - showing {sessions.length}
                </p>
              </div>
              <SoftButton
                tone="neutral"
                shape="compact"
                onClick={() => loadSessions(appliedQuery)}
                disabled={isLoadingSessions}
              >
                Refresh
              </SoftButton>
            </div>
          }
        >
          <div className="space-y-3">
            {isLoadingSessions && sessions.length === 0 ? (
              <p className="rounded-[22px] border border-dashed border-[var(--border-soft)] p-5 text-sm text-[var(--text-secondary)]">
                Loading chat sessions...
              </p>
            ) : null}

            {!isLoadingSessions && sessions.length === 0 ? (
              <p className="rounded-[22px] border border-dashed border-[var(--border-soft)] p-5 text-sm text-[var(--text-secondary)]">
                No chat sessions yet.
              </p>
            ) : null}

            {sessions.map((session) => {
              const isSelected = selectedSessionId === session.session_id;
              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => loadDetails(session.session_id)}
                  className={`block w-full rounded-[24px] border p-4 text-left transition ${
                    isSelected
                      ? "border-[var(--surface-ink)] bg-[var(--surface-ink)] text-white shadow-[var(--shadow-soft-md)]"
                      : "border-[var(--border-soft)] bg-white/80 text-[var(--text-primary)] hover:border-[var(--border-strong)] hover:bg-white"
                  }`}
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div className="min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <PillBadge tone={isSelected ? "neutral" : "dark"} size="sm">
                          {session.locale ?? "n/a"}
                        </PillBadge>
                        {session.last_active_mode ? (
                          <PillBadge tone={isSelected ? "neutral" : "accent"} size="sm">
                            {session.last_active_mode}
                          </PillBadge>
                        ) : null}
                        {session.client_ip ? (
                          <PillBadge tone={isSelected ? "neutral" : "mint"} size="sm">
                            {session.client_ip}
                          </PillBadge>
                        ) : null}
                      </div>
                      <p className="break-all font-mono text-sm font-semibold" title={session.session_id}>
                        {shortId(session.session_id)}
                      </p>
                      <p className={`text-xs ${isSelected ? "text-white/65" : "text-[var(--text-muted)]"}`}>
                        Last {formatDate(session.last_message_at)} - Started {formatDate(session.started_at)}
                      </p>
                    </div>
                    <div className="shrink-0 text-left md:text-right">
                      <p className="text-3xl font-semibold">{session.message_count}</p>
                      <p className={`text-xs ${isSelected ? "text-white/65" : "text-[var(--text-muted)]"}`}>
                        messages
                      </p>
                    </div>
                  </div>
                  <div
                    className={`mt-3 line-clamp-1 text-xs ${
                      isSelected ? "text-white/65" : "text-[var(--text-muted)]"
                    }`}
                  >
                    {session.client_user_agent_short ?? "No user-agent captured"}
                  </div>
                </button>
              );
            })}
          </div>
        </SurfaceCard>

        <ChatSessionDetailsPanel
          details={details}
          loading={isLoadingDetails}
          selectedSessionId={selectedSessionId}
        />
      </div>
    </div>
  );
}
