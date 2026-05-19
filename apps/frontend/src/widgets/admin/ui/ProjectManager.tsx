"use client";

/* eslint-disable @next/next/no-img-element -- Project screenshots can use arbitrary admin-managed media URLs. */

import { FileInput, NumberInput, Select, Switch, Textarea, TextInput } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createProject, deleteProject, getProjects, updateProject, uploadAsset } from "@/shared/api/client";
import type { Project } from "@/shared/api/types";
import {
  normalizeProjectShowcaseMeta,
  showcaseVisualOptions,
} from "@/shared/config/homepageContent";
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
  showcase_visual_variant: string;
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
  showcase_visual_variant: "dashboard-light",
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

function buildProjectPayload(form: ProjectForm): ProjectPayload {
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
      visual_variant: form.showcase_visual_variant,
      video_duration: form.showcase_video_duration,
    },
    preview_video_url: nullableString(form.preview_video_url),
    cover_image: nullableString(form.cover_image),
    repository_url: nullableString(form.repository_url),
    live_url: nullableString(form.live_url),
    page_scene_key: nullableString(form.page_scene_key),
    seo_title_ru: nullableString(form.seo_title_ru),
    seo_title_en: nullableString(form.seo_title_en),
    seo_description_ru: nullableString(form.seo_description_ru),
    seo_description_en: nullableString(form.seo_description_en),
    sort_order: form.sort_order,
    is_featured: form.is_featured,
    is_published: form.is_published,
    media_items: form.media_items
      .filter((item) => item.url.trim())
      .map((item, index) => ({
        id: item.id,
        asset_type: "image",
        url: item.url.trim(),
        alt_ru: nullableString(item.alt_ru),
        alt_en: nullableString(item.alt_en),
        sort_order: Number.isFinite(item.sort_order) ? item.sort_order : index,
      })),
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
    showcase_visual_variant: showcaseMeta.visual_variant,
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
  const [isUploadingScreenshot, setIsUploadingScreenshot] = useState(false);
  const [screenshotUploadFile, setScreenshotUploadFile] = useState<File | null>(null);

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
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
    setScreenshotUploadFile(null);
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
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <SurfaceCard variant="elevated" header={<ProjectManagerHeader count={projects.length} />}>
        <div className="space-y-3">
          {projects.map((project) => (
            <ProjectListCard
              key={project.id}
              project={project}
              isEditing={editingId === project.id}
              isDeleting={deletingId === project.id}
              onEdit={() => handleEdit(project)}
              onDelete={() => void handleDelete(project.id)}
            />
          ))}
          {projects.length === 0 ? (
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5 text-sm text-[var(--text-secondary)]">
              No projects yet.
            </div>
          ) : null}
          {error ? (
            <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      </SurfaceCard>

      <SurfaceCard
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
        <div className="space-y-4">
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

          <div className="grid gap-4 md:grid-cols-3">
            <TextInput
              label="Stack"
              placeholder="FastAPI, Next.js, Redis"
              value={form.stack}
              onChange={(event) => setForm({ ...form, stack: event.currentTarget.value })}
            />
            <TextInput
              label="Preview video URL"
              value={form.preview_video_url}
              onChange={(event) => setForm({ ...form, preview_video_url: event.currentTarget.value })}
            />
            <TextInput
              label="Cover image URL"
              value={form.cover_image}
              onChange={(event) => setForm({ ...form, cover_image: event.currentTarget.value })}
            />
          </div>

          <section className="space-y-4 border-y border-[var(--border-soft)] py-5">
            <SectionHeader
              eyebrow="Screenshots"
              title="Project gallery"
              description="Upload and order screenshots used by the public project showcase slider."
            />
            <div className="space-y-4">
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
                  <div key={`${item.id ?? "new"}-${index}`} className="grid gap-3 rounded-[20px] border border-[var(--border-soft)] bg-white/70 p-4 md:grid-cols-[110px_1fr]">
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
                    No screenshots yet. The public page will fall back to the cover image or the generated mock preview.
                  </p>
                ) : null}
              </div>
            </div>
          </section>

          <div className="grid gap-4 md:grid-cols-[1fr_0.7fr_0.6fr_0.6fr]">
            <Select
              label="Showcase visual"
              data={showcaseVisualOptions}
              value={form.showcase_visual_variant}
              onChange={(value) => setForm({ ...form, showcase_visual_variant: value ?? "dashboard-light" })}
            />
            <TextInput
              label="Video duration"
              value={form.showcase_video_duration}
              onChange={(event) => setForm({ ...form, showcase_video_duration: event.currentTarget.value })}
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

          <div className="grid gap-4 md:grid-cols-3">
            <TextInput
              label="Repository URL"
              value={form.repository_url}
              onChange={(event) => setForm({ ...form, repository_url: event.currentTarget.value })}
            />
            <TextInput
              label="Live URL"
              value={form.live_url}
              onChange={(event) => setForm({ ...form, live_url: event.currentTarget.value })}
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

function ProjectListCard({
  project,
  isEditing,
  isDeleting,
  onEdit,
  onDelete,
}: {
  project: Project;
  isEditing: boolean;
  isDeleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);

  return (
    <article className="rounded-[26px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <PillBadge tone={project.is_published ? "success" : "warning"} size="sm">
              {project.is_published ? "published" : "draft"}
            </PillBadge>
            {project.is_featured ? (
              <PillBadge tone="accent" size="sm">
                featured
              </PillBadge>
            ) : null}
            {isEditing ? (
              <PillBadge tone="dark" size="sm">
                editing
              </PillBadge>
            ) : null}
          </div>
          <div>
            <p className="font-semibold text-[var(--text-primary)]">{project.title_en}</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{project.slug}</p>
          </div>
          <p className="text-xs uppercase tracking-[0.16em] text-[var(--text-muted)]">
            {showcaseMeta.visual_variant} / {showcaseMeta.video_duration}
          </p>
          <p className="line-clamp-2 text-sm leading-6 text-[var(--text-secondary)]">{project.summary_en}</p>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
          <SoftButton tone="neutral" shape="compact" onClick={onEdit}>
            Edit
          </SoftButton>
          <SoftButton tone="accent" shape="compact" onClick={onDelete} disabled={isDeleting}>
            {isDeleting ? "Deleting..." : "Delete"}
          </SoftButton>
        </div>
      </div>
    </article>
  );
}
