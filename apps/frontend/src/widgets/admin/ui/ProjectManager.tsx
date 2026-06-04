"use client";

/* eslint-disable @next/next/no-img-element -- Project screenshots can use arbitrary admin-managed media URLs. */

import { FileInput, NumberInput, Select, Switch, Textarea, TextInput } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createProject, deleteProject, getProjects, updateProject, uploadAsset } from "@/shared/api/client";
import type { Project } from "@/shared/api/types";
import {
  isProjectType,
  normalizeProjectShowcaseMeta,
  projectTypeOptions,
  projectShowcaseMediaModeOptions,
  type ProjectType,
  type ProjectShowcaseMediaMode,
} from "@/shared/config/homepageContent";
import { cn } from "@/shared/lib/cn";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

type ProjectForm = {
  slug: string;
  title_ru: string;
  title_en: string;
  summary_ru: string;
  summary_en: string;
  description_ru: string;
  description_en: string;
  stack: string;
  project_type: ProjectType;
  showcase_media_mode: ProjectShowcaseMediaMode;
  showcase_video_duration: string;
  preview_video_url: string;
  cover_image: string;
  repository_url: string;
  live_url: string;
  page_scene_key: string;
  seo_title_ru: string;
  seo_title_en: string;
  seo_description_ru: string;
  seo_description_en: string;
  sort_order: number;
  is_featured: boolean;
  is_published: boolean;
  media_items: ProjectScreenshotFormItem[];
};

type ProjectScreenshotFormItem = {
  id?: number;
  url: string;
  alt_ru: string;
  alt_en: string;
  sort_order: number;
};

type ProjectPayload = Omit<Partial<Project>, "media_items"> & {
  media_items?: Array<{
    id?: number;
    asset_type: "image";
    url: string;
    alt_ru: string | null;
    alt_en: string | null;
    sort_order: number;
  }>;
};

const emptyForm: ProjectForm = {
  slug: "",
  title_ru: "",
  title_en: "",
  summary_ru: "",
  summary_en: "",
  description_ru: "",
  description_en: "",
  stack: "",
  project_type: "web",
  showcase_media_mode: "screenshots",
  showcase_video_duration: "0:40",
  preview_video_url: "",
  cover_image: "",
  repository_url: "",
  live_url: "",
  page_scene_key: "",
  seo_title_ru: "",
  seo_title_en: "",
  seo_description_ru: "",
  seo_description_en: "",
  sort_order: 0,
  is_featured: true,
  is_published: true,
  media_items: [],
};

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function nullableString(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function resolveProjectVisualVariant(mediaMode: ProjectShowcaseMediaMode) {
  return mediaMode === "screenshots" ? "dashboard-light" : "uploaded-media";
}

function normalizeSelectedProjectMediaMode(value: string | null): ProjectShowcaseMediaMode {
  return value === "demo" || value === "video" || value === "mobile_video" ? value : "screenshots";
}

function normalizeSelectedProjectType(value: string | null): ProjectType {
  return isProjectType(value) ? value : "web";
}

function isProjectVideoMode(mediaMode: ProjectShowcaseMediaMode) {
  return mediaMode === "video" || mediaMode === "mobile_video";
}

function sortProjectsByAdminOrder(projects: Project[]) {
  return [...projects].sort((first, second) => first.sort_order - second.sort_order || first.id - second.id);
}

function buildProjectPayload(form: ProjectForm): ProjectPayload {
  const mediaItems =
    form.showcase_media_mode === "screenshots"
      ? form.media_items
          .filter((item) => item.url.trim())
          .map((item, index) => ({
            id: item.id,
            asset_type: "image" as const,
            url: item.url.trim(),
            alt_ru: nullableString(item.alt_ru),
            alt_en: nullableString(item.alt_en),
            sort_order: Number.isFinite(item.sort_order) ? item.sort_order : index,
          }))
      : [];

  return {
    slug: nullableString(form.slug) ?? undefined,
    title_ru: form.title_ru,
    title_en: form.title_en,
    summary_ru: form.summary_ru,
    summary_en: form.summary_en,
    description_ru: form.description_ru,
    description_en: form.description_en,
    stack: parseCommaList(form.stack),
    showcase_meta: {
      project_type: normalizeSelectedProjectType(form.project_type),
      media_mode: form.showcase_media_mode,
      visual_variant: resolveProjectVisualVariant(form.showcase_media_mode),
      video_duration: form.showcase_video_duration,
    },
    preview_video_url: isProjectVideoMode(form.showcase_media_mode) ? nullableString(form.preview_video_url) : null,
    cover_image:
      form.showcase_media_mode === "demo" || isProjectVideoMode(form.showcase_media_mode)
        ? nullableString(form.cover_image)
        : null,
    repository_url: nullableString(form.repository_url),
    live_url: form.showcase_media_mode === "demo" ? nullableString(form.live_url) : null,
    page_scene_key: nullableString(form.page_scene_key),
    seo_title_ru: nullableString(form.seo_title_ru),
    seo_title_en: nullableString(form.seo_title_en),
    seo_description_ru: nullableString(form.seo_description_ru),
    seo_description_en: nullableString(form.seo_description_en),
    sort_order: form.sort_order,
    is_featured: form.is_featured,
    is_published: form.is_published,
    media_items: mediaItems,
  };
}

function buildProjectForm(project: Project): ProjectForm {
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);

  return {
    slug: project.slug,
    title_ru: project.title_ru,
    title_en: project.title_en,
    summary_ru: project.summary_ru,
    summary_en: project.summary_en,
    description_ru: project.description_ru,
    description_en: project.description_en,
    stack: project.stack.join(", "),
    project_type: normalizeSelectedProjectType(showcaseMeta.project_type),
    showcase_media_mode:
      showcaseMeta.media_mode === "video" || showcaseMeta.media_mode === "mobile_video" || showcaseMeta.media_mode === "demo"
        ? showcaseMeta.media_mode
        : "screenshots",
    showcase_video_duration: showcaseMeta.video_duration,
    preview_video_url: project.preview_video_url ?? "",
    cover_image: project.cover_image ?? "",
    repository_url: project.repository_url ?? "",
    live_url: project.live_url ?? "",
    page_scene_key: project.page_scene_key ?? "",
    seo_title_ru: project.seo_title_ru ?? "",
    seo_title_en: project.seo_title_en ?? "",
    seo_description_ru: project.seo_description_ru ?? "",
    seo_description_en: project.seo_description_en ?? "",
    sort_order: project.sort_order,
    is_featured: project.is_featured,
    is_published: project.is_published,
    media_items: project.media_items
      .filter((item) => item.asset_type === "image")
      .sort((first, second) => first.sort_order - second.sort_order)
      .map((item) => ({
        id: item.id,
        url: item.url,
        alt_ru: item.alt_ru ?? "",
        alt_en: item.alt_en ?? "",
        sort_order: item.sort_order,
      })),
  };
}

export function ProjectManager() {
  const { tokens } = useAdminAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ProjectForm>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [inlineUpdatingIds, setInlineUpdatingIds] = useState<number[]>([]);
  const [isUploadingScreenshot, setIsUploadingScreenshot] = useState(false);
  const [screenshotUploadFile, setScreenshotUploadFile] = useState<File | null>(null);
  const [isUploadingProjectVideo, setIsUploadingProjectVideo] = useState(false);
  const [isUploadingProjectCover, setIsUploadingProjectCover] = useState(false);
  const [projectVideoUploadFile, setProjectVideoUploadFile] = useState<File | null>(null);
  const [projectCoverUploadFile, setProjectCoverUploadFile] = useState<File | null>(null);

  const loadProjects = useCallback(async () => {
    if (!tokens?.access_token) {
      return;
    }
    try {
      const items = await getProjects({ includeDrafts: true }, tokens.access_token);
      setProjects(items);
      setError(null);
    } catch (nextError) {
      setProjects([]);
      setError(nextError instanceof Error ? nextError.message : "Failed to load projects");
    }
  }, [tokens?.access_token]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  function handleEdit(project: Project) {
    setEditingId(project.id);
    setForm(buildProjectForm(project));
    setScreenshotUploadFile(null);
    setProjectVideoUploadFile(null);
    setProjectCoverUploadFile(null);
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
    setScreenshotUploadFile(null);
    setProjectVideoUploadFile(null);
    setProjectCoverUploadFile(null);
  }

  async function handleSave() {
    if (!tokens?.access_token) {
      return;
    }
    setIsSaving(true);
    try {
      const payload = buildProjectPayload(form);
      if (editingId) {
        await updateProject(editingId, payload, tokens.access_token);
      } else {
        await createProject(payload, tokens.access_token);
      }
      resetForm();
      await loadProjects();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save project");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleScreenshotUpload(file: File | null) {
    if (!file || !tokens?.access_token) {
      return;
    }

    setIsUploadingScreenshot(true);
    try {
      const asset = await uploadAsset(file, tokens.access_token, "project", editingId ?? undefined);
      setForm((current) => ({
        ...current,
        media_items: [
          ...current.media_items,
          {
            url: asset.public_url,
            alt_ru: current.title_ru,
            alt_en: current.title_en,
            sort_order: current.media_items.length + 1,
          },
        ],
      }));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to upload screenshot");
    } finally {
      setIsUploadingScreenshot(false);
      setScreenshotUploadFile(null);
    }
  }

  async function handleProjectMediaUpload(field: "preview_video_url" | "cover_image", file: File | null) {
    if (!file || !tokens?.access_token) {
      return;
    }

    const isVideoUpload = field === "preview_video_url";
    if (isVideoUpload) {
      setIsUploadingProjectVideo(true);
    } else {
      setIsUploadingProjectCover(true);
    }

    try {
      const asset = await uploadAsset(file, tokens.access_token, "project", editingId ?? undefined);
      setForm((current) => ({
        ...current,
        showcase_media_mode:
          isVideoUpload && current.showcase_media_mode === "screenshots" ? "video" : current.showcase_media_mode,
        [field]: asset.public_url,
      }));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to upload project media");
    } finally {
      if (isVideoUpload) {
        setIsUploadingProjectVideo(false);
        setProjectVideoUploadFile(null);
      } else {
        setIsUploadingProjectCover(false);
        setProjectCoverUploadFile(null);
      }
    }
  }

  function updateScreenshot(index: number, patch: Partial<ProjectScreenshotFormItem>) {
    setForm((current) => ({
      ...current,
      media_items: current.media_items.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              ...patch,
            }
          : item,
      ),
    }));
  }

  function removeScreenshot(index: number) {
    setForm((current) => ({
      ...current,
      media_items: current.media_items.filter((_, itemIndex) => itemIndex !== index),
    }));
  }

  async function handleDelete(projectId: number) {
    if (!tokens?.access_token) {
      return;
    }
    setDeletingId(projectId);
    try {
      await deleteProject(projectId, tokens.access_token);
      if (editingId === projectId) {
        resetForm();
      }
      await loadProjects();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to delete project");
    } finally {
      setDeletingId(null);
    }
  }

  async function handleProjectQuickUpdate(project: Project, patch: Pick<Partial<Project>, "is_published" | "sort_order">) {
    if (!tokens?.access_token) {
      return;
    }

    setInlineUpdatingIds((current) => (current.includes(project.id) ? current : [...current, project.id]));
    setProjects((current) =>
      current.map((item) =>
        item.id === project.id
          ? {
              ...item,
              ...patch,
            }
          : item,
      ),
    );
    if (editingId === project.id) {
      setForm((current) => ({
        ...current,
        ...patch,
      }));
    }

    try {
      const updatedProject = await updateProject(project.id, patch, tokens.access_token);
      setProjects((current) => current.map((item) => (item.id === project.id ? updatedProject : item)));
      setError(null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to update project");
      await loadProjects();
    } finally {
      setInlineUpdatingIds((current) => current.filter((id) => id !== project.id));
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <ProjectManagerHeader count={0} />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to create, edit, and delete portfolio projects.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <SurfaceCard className="order-2" variant="elevated" header={<ProjectManagerHeader count={projects.length} />}>
        <div className="space-y-5">
          <ProjectTypeTables
            projects={projects}
            editingId={editingId}
            deletingId={deletingId}
            inlineUpdatingIds={inlineUpdatingIds}
            onEdit={handleEdit}
            onDelete={(projectId) => void handleDelete(projectId)}
            onQuickUpdate={(project, patch) => void handleProjectQuickUpdate(project, patch)}
          />
          {error ? (
            <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      </SurfaceCard>

      <SurfaceCard
        className="order-1"
        variant="default"
        header={
          <SectionHeader
            eyebrow="Project form"
            title={editingId ? "Edit project" : "Create project"}
            description="Maintain bilingual portfolio copy and media references from the same admin surface."
            action={
              editingId ? (
                <SoftButton tone="neutral" onClick={resetForm}>
                  Cancel edit
                </SoftButton>
              ) : null
            }
          />
        }
      >
        <div className="space-y-5">
          <section className="space-y-4 rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
            <SectionHeader
              eyebrow="Content"
              title="Project copy"
              description="Main bilingual text, stack and publication state."
            />
            <div className="grid gap-4 md:grid-cols-2">
              <TextInput
                label="Slug"
                description="Leave empty for a new project to generate it from Title EN."
                value={form.slug}
                onChange={(event) => setForm({ ...form, slug: event.currentTarget.value })}
              />
              <NumberInput
                label="Sort order"
                value={form.sort_order}
                onChange={(value) => setForm({ ...form, sort_order: typeof value === "number" ? value : 0 })}
              />
              <Select
                label="Project type"
                data={projectTypeOptions}
                required
                value={form.project_type}
                onChange={(value) =>
                  setForm({
                    ...form,
                    project_type: normalizeSelectedProjectType(value),
                  })
                }
              />
              <TextInput
                label="Title RU"
                value={form.title_ru}
                onChange={(event) => setForm({ ...form, title_ru: event.currentTarget.value })}
              />
              <TextInput
                label="Title EN"
                value={form.title_en}
                onChange={(event) => setForm({ ...form, title_en: event.currentTarget.value })}
              />
              <Textarea
                label="Summary RU"
                value={form.summary_ru}
                onChange={(event) => setForm({ ...form, summary_ru: event.currentTarget.value })}
              />
              <Textarea
                label="Summary EN"
                value={form.summary_en}
                onChange={(event) => setForm({ ...form, summary_en: event.currentTarget.value })}
              />
            </div>

            <Textarea
              label="Description RU"
              minRows={4}
              value={form.description_ru}
              onChange={(event) => setForm({ ...form, description_ru: event.currentTarget.value })}
            />
            <Textarea
              label="Description EN"
              minRows={4}
              value={form.description_en}
              onChange={(event) => setForm({ ...form, description_en: event.currentTarget.value })}
            />

            <div className="grid gap-4 md:grid-cols-[1fr_0.45fr_0.45fr]">
              <TextInput
                label="Stack"
                placeholder="FastAPI, Next.js, Redis"
                value={form.stack}
                onChange={(event) => setForm({ ...form, stack: event.currentTarget.value })}
              />
              <Switch
                className="self-end pb-2"
                label="Featured"
                checked={form.is_featured}
                onChange={(event) => setForm({ ...form, is_featured: event.currentTarget.checked })}
              />
              <Switch
                className="self-end pb-2"
                label="Published"
                checked={form.is_published}
                onChange={(event) => setForm({ ...form, is_published: event.currentTarget.checked })}
              />
            </div>
          </section>

          <section className="space-y-4 rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
            <SectionHeader
              eyebrow="Homepage"
              title="Project media"
              description="Choose one public media mode. Fields that do not belong to the selected mode are hidden."
            />
            <Select
              label="Media type"
              data={projectShowcaseMediaModeOptions}
              value={form.showcase_media_mode}
              onChange={(value) =>
                setForm({
                  ...form,
                  showcase_media_mode: normalizeSelectedProjectMediaMode(value),
                })
              }
            />

            {form.showcase_media_mode === "screenshots" ? (
              <div className="space-y-4 border-t border-[var(--border-soft)] pt-4">
                <SectionHeader
                  eyebrow="Screenshots"
                  title="Project gallery"
                  description="Upload and order screenshots used by the public slider."
                />
                <FileInput
                  label="Upload screenshot"
                  description="PNG, JPG, WebP or AVIF."
                  accept="image/*"
                  clearable
                  disabled={isUploadingScreenshot || !tokens?.access_token}
                  placeholder={isUploadingScreenshot ? "Uploading..." : "Choose screenshot"}
                  value={screenshotUploadFile}
                  onChange={(file) => {
                    setScreenshotUploadFile(file);
                    void handleScreenshotUpload(file);
                  }}
                />

                <div className="space-y-3">
                  {form.media_items.map((item, index) => (
                    <div
                      key={`${item.id ?? "new"}-${index}`}
                      className="grid gap-3 rounded-[20px] border border-[var(--border-soft)] bg-white/70 p-4 md:grid-cols-[110px_1fr]"
                    >
                      <div className="aspect-video overflow-hidden rounded-md bg-slate-950">
                        {item.url ? <img src={item.url} alt="" className="h-full w-full object-cover" /> : null}
                      </div>
                      <div className="grid gap-3 md:grid-cols-2">
                        <TextInput
                          label="Screenshot URL"
                          value={item.url}
                          onChange={(event) => updateScreenshot(index, { url: event.currentTarget.value })}
                        />
                        <NumberInput
                          label="Sort"
                          value={item.sort_order}
                          onChange={(value) =>
                            updateScreenshot(index, { sort_order: typeof value === "number" ? value : index })
                          }
                        />
                        <TextInput
                          label="Alt RU"
                          value={item.alt_ru}
                          onChange={(event) => updateScreenshot(index, { alt_ru: event.currentTarget.value })}
                        />
                        <TextInput
                          label="Alt EN"
                          value={item.alt_en}
                          onChange={(event) => updateScreenshot(index, { alt_en: event.currentTarget.value })}
                        />
                        <div className="md:col-span-2">
                          <SoftButton tone="accent" shape="compact" onClick={() => removeScreenshot(index)}>
                            Remove screenshot
                          </SoftButton>
                        </div>
                      </div>
                    </div>
                  ))}
                  {form.media_items.length === 0 ? (
                    <p className="text-sm text-[var(--text-secondary)]">
                      No screenshots yet. In screenshots mode the public card stays text-only until images are added.
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}

            {form.showcase_media_mode === "demo" ? (
              <div className="space-y-4 border-t border-[var(--border-soft)] pt-4">
                <SectionHeader
                  eyebrow="Demo"
                  title="Demo preview"
                  description="The image is used only as a dimmed background for the demo button."
                />
                <div className="grid gap-4 md:grid-cols-2">
                  <TextInput
                    label="Demo preview image URL"
                    value={form.cover_image}
                    onChange={(event) => setForm({ ...form, cover_image: event.currentTarget.value })}
                  />
                  <FileInput
                    label="Upload demo preview"
                    description="PNG, JPG, WebP or AVIF."
                    accept="image/*"
                    clearable
                    disabled={isUploadingProjectCover || !tokens?.access_token}
                    placeholder={isUploadingProjectCover ? "Uploading..." : "Choose image"}
                    value={projectCoverUploadFile}
                    onChange={(file) => {
                      setProjectCoverUploadFile(file);
                      void handleProjectMediaUpload("cover_image", file);
                    }}
                  />
                  <TextInput
                    className="md:col-span-2"
                    label="Demo URL"
                    description="Rendered as a JS-opened button on the public page, not as a plain HTML link."
                    value={form.live_url}
                    onChange={(event) => setForm({ ...form, live_url: event.currentTarget.value })}
                  />
                </div>
              </div>
            ) : null}

            {isProjectVideoMode(form.showcase_media_mode) ? (
              <div className="space-y-4 border-t border-[var(--border-soft)] pt-4">
                <SectionHeader
                  eyebrow={form.showcase_media_mode === "mobile_video" ? "Mobile video" : "Video"}
                  title={form.showcase_media_mode === "mobile_video" ? "Phone screen recording" : "Project video preview"}
                  description={
                    form.showcase_media_mode === "mobile_video"
                      ? "Upload a vertical phone screen recording and an optional poster image."
                      : "Upload a demo video and poster image used by the public homepage video player."
                  }
                />
                <div className="grid gap-4 md:grid-cols-2">
                  <TextInput
                    label={form.showcase_media_mode === "mobile_video" ? "Mobile video URL" : "Video URL"}
                    value={form.preview_video_url}
                    onChange={(event) => setForm({ ...form, preview_video_url: event.currentTarget.value })}
                  />
                  <FileInput
                    label={form.showcase_media_mode === "mobile_video" ? "Upload mobile video" : "Upload video"}
                    description="MP4, WebM or MOV."
                    accept="video/*"
                    clearable
                    disabled={isUploadingProjectVideo || !tokens?.access_token}
                    placeholder={isUploadingProjectVideo ? "Uploading..." : "Choose video"}
                    value={projectVideoUploadFile}
                    onChange={(file) => {
                      setProjectVideoUploadFile(file);
                      void handleProjectMediaUpload("preview_video_url", file);
                    }}
                  />
                  <TextInput
                    label={form.showcase_media_mode === "mobile_video" ? "Mobile video poster URL" : "Video preview image URL"}
                    value={form.cover_image}
                    onChange={(event) => setForm({ ...form, cover_image: event.currentTarget.value })}
                  />
                  <FileInput
                    label={form.showcase_media_mode === "mobile_video" ? "Upload mobile video poster" : "Upload video preview"}
                    description="PNG, JPG, WebP or AVIF."
                    accept="image/*"
                    clearable
                    disabled={isUploadingProjectCover || !tokens?.access_token}
                    placeholder={isUploadingProjectCover ? "Uploading..." : "Choose image"}
                    value={projectCoverUploadFile}
                    onChange={(file) => {
                      setProjectCoverUploadFile(file);
                      void handleProjectMediaUpload("cover_image", file);
                    }}
                  />
                  <TextInput
                    label="Fallback duration"
                    value={form.showcase_video_duration}
                    onChange={(event) => setForm({ ...form, showcase_video_duration: event.currentTarget.value })}
                  />
                </div>
              </div>
            ) : null}
          </section>

          <section className="space-y-4 rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-4">
            <SectionHeader
              eyebrow="Metadata"
              title="Links and SEO"
              description="Secondary links and search snippets for project pages."
            />
            <div className="grid gap-4 md:grid-cols-2">
              <TextInput
                label="Repository URL"
                value={form.repository_url}
                onChange={(event) => setForm({ ...form, repository_url: event.currentTarget.value })}
              />
              <TextInput
                label="Page scene key"
                value={form.page_scene_key}
                onChange={(event) => setForm({ ...form, page_scene_key: event.currentTarget.value })}
              />
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <TextInput
                label="SEO title RU"
                value={form.seo_title_ru}
                onChange={(event) => setForm({ ...form, seo_title_ru: event.currentTarget.value })}
              />
              <TextInput
                label="SEO title EN"
                value={form.seo_title_en}
                onChange={(event) => setForm({ ...form, seo_title_en: event.currentTarget.value })}
              />
              <Textarea
                label="SEO description RU"
                minRows={3}
                value={form.seo_description_ru}
                onChange={(event) => setForm({ ...form, seo_description_ru: event.currentTarget.value })}
              />
              <Textarea
                label="SEO description EN"
                minRows={3}
                value={form.seo_description_en}
                onChange={(event) => setForm({ ...form, seo_description_en: event.currentTarget.value })}
              />
            </div>
          </section>

          <SoftButton tone="dark" onClick={() => void handleSave()} disabled={isSaving}>
            {isSaving ? "Saving..." : editingId ? "Update project" : "Create project"}
          </SoftButton>
        </div>
      </SurfaceCard>
    </div>
  );
}

function ProjectManagerHeader({ count }: { count: number }) {
  return (
    <SectionHeader
      eyebrow="Portfolio CMS"
      title="Projects"
      description="Create and maintain project cards for the public homepage and project archive."
      action={
        <PillBadge tone="dark">
          {count} total
        </PillBadge>
      }
    />
  );
}

function ProjectTypeTables({
  projects,
  editingId,
  deletingId,
  inlineUpdatingIds,
  onEdit,
  onDelete,
  onQuickUpdate,
}: {
  projects: Project[];
  editingId: number | null;
  deletingId: number | null;
  inlineUpdatingIds: number[];
  onEdit: (project: Project) => void;
  onDelete: (projectId: number) => void;
  onQuickUpdate: (project: Project, patch: Pick<Partial<Project>, "is_published" | "sort_order">) => void;
}) {
  return (
    <div className="space-y-6">
      {projectTypeOptions.map((typeOption) => {
        const typeProjects = sortProjectsByAdminOrder(
          projects.filter(
            (project) => normalizeProjectShowcaseMeta(project.showcase_meta).project_type === typeOption.value,
          ),
        );

        return (
          <ProjectTypeTable
            key={typeOption.value}
            title={typeOption.label}
            projects={typeProjects}
            editingId={editingId}
            deletingId={deletingId}
            inlineUpdatingIds={inlineUpdatingIds}
            onEdit={onEdit}
            onDelete={onDelete}
            onQuickUpdate={onQuickUpdate}
          />
        );
      })}
    </div>
  );
}

function ProjectTypeTable({
  title,
  projects,
  editingId,
  deletingId,
  inlineUpdatingIds,
  onEdit,
  onDelete,
  onQuickUpdate,
}: {
  title: string;
  projects: Project[];
  editingId: number | null;
  deletingId: number | null;
  inlineUpdatingIds: number[];
  onEdit: (project: Project) => void;
  onDelete: (projectId: number) => void;
  onQuickUpdate: (project: Project, patch: Pick<Partial<Project>, "is_published" | "sort_order">) => void;
}) {
  return (
    <section className="overflow-hidden rounded-[24px] border border-[var(--border-soft)] bg-white/72">
      <div className="flex items-center justify-between gap-4 border-b border-[var(--border-soft)] bg-[var(--surface-secondary)] px-4 py-3">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--text-primary)]">{title}</h3>
          <PillBadge tone="neutral" size="sm">
            {projects.length}
          </PillBadge>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-[860px] w-full border-collapse text-left text-sm">
          <thead className="bg-white/55 text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-3 font-semibold">Project</th>
              <th className="px-4 py-3 font-semibold">Media</th>
              <th className="w-[132px] px-4 py-3 font-semibold">Active</th>
              <th className="w-[132px] px-4 py-3 font-semibold">Order</th>
              <th className="w-[176px] px-4 py-3 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-soft)]">
            {projects.length > 0 ? (
              projects.map((project) => (
                <ProjectTableRow
                  key={project.id}
                  project={project}
                  isEditing={editingId === project.id}
                  isDeleting={deletingId === project.id}
                  isUpdating={inlineUpdatingIds.includes(project.id)}
                  onEdit={() => onEdit(project)}
                  onDelete={() => onDelete(project.id)}
                  onQuickUpdate={(patch) => onQuickUpdate(project, patch)}
                />
              ))
            ) : (
              <tr>
                <td className="px-4 py-5 text-sm text-[var(--text-secondary)]" colSpan={5}>
                  No projects in this type yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ProjectTableRow({
  project,
  isEditing,
  isDeleting,
  isUpdating,
  onEdit,
  onDelete,
  onQuickUpdate,
}: {
  project: Project;
  isEditing: boolean;
  isDeleting: boolean;
  isUpdating: boolean;
  onEdit: () => void;
  onDelete: () => void;
  onQuickUpdate: (patch: Pick<Partial<Project>, "is_published" | "sort_order">) => void;
}) {
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);

  return (
    <tr className={cn("align-top transition", isEditing ? "bg-[#fff8ef]" : "hover:bg-white/70")}>
      <td className="px-4 py-4">
        <div className="max-w-[360px]">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold text-[var(--text-primary)]">{project.title_en}</p>
            {isEditing ? (
              <PillBadge tone="dark" size="sm">
                editing
              </PillBadge>
            ) : null}
            {isUpdating ? (
              <PillBadge tone="subtle" size="sm">
                saving
              </PillBadge>
            ) : null}
          </div>
          <p className="mt-1 text-xs text-[var(--text-muted)]">{project.slug}</p>
          <p className="mt-2 line-clamp-2 text-sm leading-6 text-[var(--text-secondary)]">{project.summary_en}</p>
        </div>
      </td>
      <td className="px-4 py-4">
        <PillBadge tone="neutral" size="sm">
          {showcaseMeta.media_mode}
        </PillBadge>
      </td>
      <td className="px-4 py-4">
        <Switch
          checked={project.is_published}
          disabled={isDeleting}
          onChange={(event) => onQuickUpdate({ is_published: event.currentTarget.checked })}
        />
      </td>
      <td className="px-4 py-4">
        <NumberInput
          hideControls
          min={0}
          value={project.sort_order}
          className="w-24"
          disabled={isDeleting}
          onChange={(value) => {
            const nextValue = typeof value === "number" ? value : Number(value);
            if (Number.isFinite(nextValue) && nextValue !== project.sort_order) {
              onQuickUpdate({ sort_order: Math.round(nextValue) });
            }
          }}
        />
      </td>
      <td className="px-4 py-4">
        <div className="flex justify-end gap-2">
          <SoftButton tone="neutral" shape="compact" onClick={onEdit}>
            Edit
          </SoftButton>
          <SoftButton tone="accent" shape="compact" onClick={onDelete} disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete"}
          </SoftButton>
        </div>
      </td>
    </tr>
  );
}
