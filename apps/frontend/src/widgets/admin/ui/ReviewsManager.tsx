"use client";

import { NumberInput, Switch, Textarea, TextInput } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import {
  getAdminKworkReviews,
  getSiteSettings,
  syncKworkReviews,
  updateKworkReview,
  updateSiteSettings,
} from "@/shared/api/client";
import type { KworkReview, SiteSettings } from "@/shared/api/types";
import { normalizeHomepageContent } from "@/shared/config/homepageContent";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";
import { buildSiteSettingsUpdatePayload } from "@/widgets/admin/model/siteSettingsPayload";

type ReviewsStatus = "idle" | "loading" | "ready" | "error";

const DEFAULT_SOURCE_URL = "https://kwork.ru/user/portfolio-dev";
const ADMIN_PAGE_SIZE = 6;

export function ReviewsManager() {
  const { tokens } = useAdminAuth();
  const [items, setItems] = useState<KworkReview[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [sourceUrl, setSourceUrl] = useState(DEFAULT_SOURCE_URL);
  const [replace, setReplace] = useState(true);
  const [limit, setLimit] = useState(100);
  const [status, setStatus] = useState<ReviewsStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [eyebrowRu, setEyebrowRu] = useState("");
  const [eyebrowEn, setEyebrowEn] = useState("");
  const [titleRu, setTitleRu] = useState("");
  const [titleEn, setTitleEn] = useState("");
  const [isSavingTitle, setIsSavingTitle] = useState(false);

  const loadReviews = useCallback(async () => {
    if (!tokens?.access_token) {
      setStatus("idle");
      return;
    }
    setStatus("loading");
    try {
      const reviewsPage = await getAdminKworkReviews(tokens.access_token, {
        offset: page * ADMIN_PAGE_SIZE,
        limit: ADMIN_PAGE_SIZE,
      });
      setItems(reviewsPage.items);
      setTotal(reviewsPage.total);
      setError(null);
      setStatus("ready");
    } catch (nextError) {
      setItems([]);
      setTotal(0);
      setError(nextError instanceof Error ? nextError.message : "Failed to load reviews");
      setStatus("error");
    }
  }, [page, tokens?.access_token]);

  useEffect(() => {
    void loadReviews();
  }, [loadReviews]);

  useEffect(() => {
    if (!tokens?.access_token) {
      return;
    }

    let cancelled = false;
    getSiteSettings()
      .then((nextSettings) => {
        if (cancelled) {
          return;
        }
        const normalizedContent = normalizeHomepageContent(nextSettings.homepage_content);
        const normalizedSettings = {
          ...nextSettings,
          homepage_content: normalizedContent,
        };
        setSettings(normalizedSettings);
        setEyebrowRu(normalizedContent.kwork_reviews_eyebrow_ru);
        setEyebrowEn(normalizedContent.kwork_reviews_eyebrow_en);
        setTitleRu(normalizedContent.kwork_reviews_title_ru);
        setTitleEn(normalizedContent.kwork_reviews_title_en);
      })
      .catch((nextError) => {
        if (!cancelled) {
          setError(nextError instanceof Error ? nextError.message : "Failed to load review title settings");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [tokens?.access_token]);

  async function handleSync() {
    if (!tokens?.access_token) {
      return;
    }
    setSyncing(true);
    setNotice(null);
    try {
      const result = await syncKworkReviews(
        {
          source_url: sourceUrl,
          replace,
          limit,
        },
        tokens.access_token,
      );
      setItems(result.page.items);
      setTotal(result.page.total);
      setPage(0);
      setError(null);
      setNotice(`Imported ${result.imported} reviews. Total in database: ${result.total}.`);
      setStatus("ready");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to sync Kwork reviews");
    } finally {
      setSyncing(false);
    }
  }

  function patchReview(id: number, patch: Partial<KworkReview>) {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function handleSave(review: KworkReview) {
    if (!tokens?.access_token) {
      return;
    }
    setSavingId(review.id);
    try {
      const updated = await updateKworkReview(
        review.id,
        {
          author_name: review.author_name,
          author_url: review.author_url,
          project_title: review.project_title,
          project_url: review.project_url,
          rating: review.rating,
          text: review.text,
          sort_order: review.sort_order,
          is_published: review.is_published,
        },
        tokens.access_token,
      );
      patchReview(updated.id, updated);
      setError(null);
      setNotice("Review saved.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save review");
    } finally {
      setSavingId(null);
    }
  }

  async function handleSaveTitles() {
    if (!tokens?.access_token || !settings) {
      return;
    }
    setIsSavingTitle(true);
    try {
      const nextSettings = {
        ...settings,
        homepage_content: normalizeHomepageContent({
          ...settings.homepage_content,
          kwork_reviews_eyebrow_ru: eyebrowRu,
          kwork_reviews_eyebrow_en: eyebrowEn,
          kwork_reviews_title_ru: titleRu,
          kwork_reviews_title_en: titleEn,
        }),
      };
      const updated = await updateSiteSettings(
        buildSiteSettingsUpdatePayload(nextSettings),
        tokens.access_token,
      );
      const normalizedContent = normalizeHomepageContent(updated.homepage_content);
      setSettings({
        ...updated,
        homepage_content: normalizedContent,
      });
      setEyebrowRu(normalizedContent.kwork_reviews_eyebrow_ru);
      setEyebrowEn(normalizedContent.kwork_reviews_eyebrow_en);
      setTitleRu(normalizedContent.kwork_reviews_title_ru);
      setTitleEn(normalizedContent.kwork_reviews_title_en);
      setNotice("Review section titles saved.");
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save review titles");
    } finally {
      setIsSavingTitle(false);
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <ReviewsHeader statusLabel="auth required" />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to parse and edit public Kwork reviews.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <SurfaceCard
      variant="elevated"
      header={<ReviewsHeader statusLabel={syncing ? "syncing" : status === "loading" ? "loading" : "editable"} />}
    >
      <div className="space-y-6">
        <div className="grid gap-4 rounded-[24px] border border-[var(--border-soft)] bg-white/70 p-5 md:grid-cols-2 md:items-end">
          <TextInput
            label="Reviews eyebrow RU"
            value={eyebrowRu}
            onChange={(event) => setEyebrowRu(event.currentTarget.value)}
          />
          <TextInput
            label="Reviews eyebrow EN"
            value={eyebrowEn}
            onChange={(event) => setEyebrowEn(event.currentTarget.value)}
          />
          <TextInput
            label="Reviews title RU"
            value={titleRu}
            onChange={(event) => setTitleRu(event.currentTarget.value)}
          />
          <TextInput
            label="Reviews title EN"
            value={titleEn}
            onChange={(event) => setTitleEn(event.currentTarget.value)}
          />
          <div className="md:col-span-2">
            <SoftButton
              tone="dark"
              onClick={() => void handleSaveTitles()}
              disabled={!settings || isSavingTitle}
            >
              {isSavingTitle ? "Saving titles..." : "Save review titles"}
            </SoftButton>
          </div>
        </div>

        <div className="grid gap-4 rounded-[24px] border border-[var(--border-soft)] bg-white/70 p-5 lg:grid-cols-[1fr_140px_120px_auto] lg:items-end">
          <TextInput
            label="Kwork profile URL"
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.currentTarget.value)}
          />
          <NumberInput
            label="Limit"
            min={1}
            max={200}
            value={limit}
            onChange={(value) => setLimit(Number(value) || 100)}
          />
          <Switch
            label="Replace"
            checked={replace}
            onChange={(event) => setReplace(event.currentTarget.checked)}
          />
          <SoftButton tone="dark" onClick={() => void handleSync()} disabled={syncing}>
            {syncing ? "Parsing..." : "Parse reviews"}
          </SoftButton>
        </div>

        {notice ? (
          <div className="rounded-[20px] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            {notice}
          </div>
        ) : null}
        {error ? (
          <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-2">
          {items.map((item) => (
            <ReviewEditorCard
              key={item.id}
              item={item}
              isSaving={savingId === item.id}
              onPatch={(patch) => patchReview(item.id, patch)}
              onSave={() => void handleSave(item)}
            />
          ))}
        </div>

        {total > ADMIN_PAGE_SIZE ? (
          <AdminReviewsPagination
            page={page}
            total={total}
            pageSize={ADMIN_PAGE_SIZE}
            onPageChange={setPage}
          />
        ) : null}

        {items.length === 0 ? (
          <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5 text-sm text-[var(--text-secondary)]">
            {status === "loading" ? "Loading reviews..." : "No reviews in the database yet."}
          </div>
        ) : null}
      </div>
    </SurfaceCard>
  );
}

function AdminReviewsPagination({
  page,
  total,
  pageSize,
  onPageChange,
}: {
  page: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const start = page * pageSize + 1;
  const end = Math.min(total, (page + 1) * pageSize);

  return (
    <div className="flex flex-col gap-3 rounded-[22px] border border-[var(--border-soft)] bg-white/70 p-4 text-sm text-[var(--text-secondary)] sm:flex-row sm:items-center sm:justify-between">
      <span>
        Showing {start}-{end} of {total}
      </span>
      <div className="flex items-center gap-2">
        <SoftButton
          tone="neutral"
          shape="compact"
          disabled={page <= 0}
          onClick={() => onPageChange(Math.max(0, page - 1))}
        >
          Previous
        </SoftButton>
        <span className="px-2 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--text-muted)]">
          {page + 1} / {pageCount}
        </span>
        <SoftButton
          tone="neutral"
          shape="compact"
          disabled={page >= pageCount - 1}
          onClick={() => onPageChange(Math.min(pageCount - 1, page + 1))}
        >
          Next
        </SoftButton>
      </div>
    </div>
  );
}

function ReviewsHeader({ statusLabel }: { statusLabel: string }) {
  return (
    <SectionHeader
      eyebrow="Kwork social proof"
      title="Reviews"
      description="Parse reviews from your Kwork profile, review imported text, and control which cards appear on the homepage."
      action={<PillBadge tone="dark">{statusLabel}</PillBadge>}
    />
  );
}

function ReviewEditorCard({
  item,
  isSaving,
  onPatch,
  onSave,
}: {
  item: KworkReview;
  isSaving: boolean;
  onPatch: (patch: Partial<KworkReview>) => void;
  onSave: () => void;
}) {
  return (
    <article className="space-y-4 rounded-[24px] border border-[var(--border-soft)] bg-white/80 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--text-muted)]">
            {item.review_type} / {item.reviewed_at?.slice(0, 10) || item.time_ago || "Kwork"}
          </p>
          <h3 className="mt-2 text-xl font-semibold text-[var(--text-primary)]">{item.author_name}</h3>
        </div>
        <Switch
          label="Published"
          checked={item.is_published}
          onChange={(event) => onPatch({ is_published: event.currentTarget.checked })}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <TextInput
          label="Author"
          value={item.author_name}
          onChange={(event) => onPatch({ author_name: event.currentTarget.value })}
        />
        <TextInput
          label="Author URL"
          value={item.author_url ?? ""}
          onChange={(event) => onPatch({ author_url: event.currentTarget.value })}
        />
        <NumberInput
          label="Rating"
          min={1}
          max={5}
          value={item.rating}
          onChange={(value) => onPatch({ rating: Number(value) || 5 })}
        />
        <NumberInput
          label="Sort order"
          value={item.sort_order}
          onChange={(value) => onPatch({ sort_order: Number(value) || 0 })}
        />
      </div>

      <TextInput
        label="Project title"
        value={item.project_title ?? ""}
        onChange={(event) => onPatch({ project_title: event.currentTarget.value })}
      />
      <Textarea
        label="Review text"
        minRows={4}
        value={item.text}
        onChange={(event) => onPatch({ text: event.currentTarget.value })}
      />

      <div className="flex justify-end">
        <SoftButton tone="dark" onClick={onSave} disabled={isSaving}>
          {isSaving ? "Saving..." : "Save review"}
        </SoftButton>
      </div>
    </article>
  );
}
