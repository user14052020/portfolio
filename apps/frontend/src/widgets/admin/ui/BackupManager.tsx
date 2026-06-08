"use client";

import { Checkbox, FileInput } from "@mantine/core";
import { useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { downloadSiteBackup, restoreSiteBackup } from "@/shared/api/client";
import type { BackupRestoreResult } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

const tableLabels: Record<string, string> = {
  site_settings: "Site settings",
  page_scenes: "Page scenes",
  style_ingestion_runtime_settings: "Parser settings",
  blog_categories: "Blog categories",
  blog_posts: "Blog posts",
  projects: "Projects",
  project_media: "Project media",
  kwork_reviews: "Kwork reviews",
  contact_requests: "Contact requests",
};

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 500);
}

export function BackupManager() {
  const { tokens } = useAdminAuth();
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isRestoreConfirmed, setIsRestoreConfirmed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [restoreResult, setRestoreResult] = useState<BackupRestoreResult | null>(null);

  async function handleDownload() {
    if (!tokens?.access_token) {
      return;
    }

    setIsDownloading(true);
    setError(null);
    setNotice(null);
    setRestoreResult(null);

    try {
      const backup = await downloadSiteBackup(tokens.access_token);
      saveBlob(backup.blob, backup.filename);
      setNotice("Backup archive is ready for download.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to download backup.");
    } finally {
      setIsDownloading(false);
    }
  }

  async function handleRestore() {
    if (!tokens?.access_token || !backupFile || !isRestoreConfirmed) {
      return;
    }

    const confirmed = window.confirm(
      "Restore this backup? Current content records will be replaced with data from the archive.",
    );
    if (!confirmed) {
      return;
    }

    setIsRestoring(true);
    setError(null);
    setNotice(null);
    setRestoreResult(null);

    try {
      const result = await restoreSiteBackup(backupFile, tokens.access_token);
      setRestoreResult(result);
      setBackupFile(null);
      setIsRestoreConfirmed(false);
      setNotice("Backup restored successfully.");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to restore backup.");
    } finally {
      setIsRestoring(false);
    }
  }

  const restoredEntries = Object.entries(restoreResult?.restored ?? {});

  return (
    <div className="space-y-7">
      <SectionHeader
        eyebrow="Archive"
        title="Backup"
        description="Download a full content archive with media files or restore the site content from a previous archive."
        action={<PillBadge tone="neutral">ZIP</PillBadge>}
      />

      <div className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <SurfaceCard
          variant="elevated"
          header={
            <SectionHeader
              eyebrow="Export"
              title="Download backup"
              description="Includes site content, projects, reviews, posts, contact requests and all files from the media directory."
            />
          }
        >
          <div className="space-y-5">
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-white/70 p-5 text-sm leading-6 text-[var(--text-secondary)]">
              Users, roles, passwords, chat sessions and generation jobs are intentionally excluded from this archive.
            </div>
            <SoftButton tone="dark" shape="surface" onClick={() => void handleDownload()} disabled={isDownloading}>
              {isDownloading ? "Preparing archive..." : "Download ZIP backup"}
            </SoftButton>
          </div>
        </SurfaceCard>

        <SurfaceCard
          variant="default"
          header={
            <SectionHeader
              eyebrow="Import"
              title="Restore from backup"
              description="Use only archives created by this admin panel. Content tables will be replaced; existing media files not present in the archive are left in place."
            />
          }
        >
          <div className="space-y-5">
            <FileInput
              label="Backup archive"
              description="ZIP archive exported from this site."
              placeholder="Choose .zip file"
              accept=".zip,application/zip,application/x-zip-compressed"
              value={backupFile}
              onChange={setBackupFile}
            />
            <Checkbox
              checked={isRestoreConfirmed}
              onChange={(event) => setIsRestoreConfirmed(event.currentTarget.checked)}
              label="I understand that current content records will be replaced by the backup data."
            />
            <SoftButton
              tone="dark"
              shape="surface"
              onClick={() => void handleRestore()}
              disabled={!backupFile || !isRestoreConfirmed || isRestoring}
            >
              {isRestoring ? "Restoring..." : "Restore backup"}
            </SoftButton>
          </div>
        </SurfaceCard>
      </div>

      {notice ? (
        <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          {notice}
        </div>
      ) : null}
      {error ? (
        <div className="rounded-[24px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {restoreResult ? (
        <SurfaceCard
          variant="soft"
          header={
            <SectionHeader
              eyebrow="Restore report"
              title="Restored content"
              description={`${restoreResult.media_files_restored} media files restored.`}
            />
          }
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {restoredEntries.map(([key, count]) => (
              <div key={key} className="rounded-[20px] border border-[var(--border-soft)] bg-white/70 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-[var(--text-muted)]">
                  {tableLabels[key] ?? key}
                </p>
                <p className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{count}</p>
              </div>
            ))}
          </div>
          {restoreResult.warnings.length ? (
            <div className="mt-5 rounded-[24px] border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
              {restoreResult.warnings.map((warning) => (
                <p key={warning}>{warning}</p>
              ))}
            </div>
          ) : null}
        </SurfaceCard>
      ) : null}
    </div>
  );
}
