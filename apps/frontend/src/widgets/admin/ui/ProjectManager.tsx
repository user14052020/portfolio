"use client";

import { NumberInput, Select, Switch, Textarea, TextInput } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createProject, deleteProject, getProjects, updateProject } from "@/shared/api/client";
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
  sort_order: number;
  is_featured: boolean;
  is_published: boolean;
};

const emptyForm: ProjectForm = {
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
  sort_order: 0,
  is_featured: true,
  is_published: true,
};

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildProjectPayload(form: ProjectForm): Partial<Project> {
  return {
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
    preview_video_url: form.preview_video_url,
    cover_image: form.cover_image,
    sort_order: form.sort_order,
    is_featured: form.is_featured,
    is_published: form.is_published,
  };
}

function buildProjectForm(project: Project): ProjectForm {
  const showcaseMeta = normalizeProjectShowcaseMeta(project.showcase_meta);

  return {
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
    sort_order: project.sort_order,
    is_featured: project.is_featured,
    is_published: project.is_published,
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
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
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
          <div className="grid gap-4 md:grid-cols-[1fr_0.65fr_0.55fr_0.55fr_0.55fr]">
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
            <NumberInput
              label="Sort order"
              value={form.sort_order}
              onChange={(value) => setForm({ ...form, sort_order: typeof value === "number" ? value : 0 })}
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
