"use client";

import { Button, Stack, TextInput, Textarea } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createProject, deleteProject, getProjects, updateProject } from "@/shared/api/client";
import type { Project } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

const emptyForm = {
  title_ru: "",
  title_en: "",
  summary_ru: "",
  summary_en: "",
  description_ru: "",
  description_en: "",
  stack: "",
  preview_video_url: "",
  cover_image: ""
};

export function ProjectManager() {
  const { tokens } = useAdminAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);

  const loadProjects = useCallback(async () => {
    if (!tokens?.access_token) {
      return;
    }
    const items = await getProjects({ includeDrafts: true }, tokens.access_token);
    setProjects(items);
  }, [tokens?.access_token]);

  useEffect(() => {
    void loadProjects();
  }, [loadProjects]);

  const handleSave = async () => {
    if (!tokens?.access_token) {
      return;
    }
    const payload = {
      ...form,
      stack: form.stack.split(",").map((item) => item.trim()).filter(Boolean)
    };
    if (editingId) {
      await updateProject(editingId, payload, tokens.access_token);
    } else {
      await createProject(payload, tokens.access_token);
    }
    setForm(emptyForm);
    setEditingId(null);
    await loadProjects();
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <WindowFrame title="Projects" subtitle="CRUD">
        <div className="space-y-3">
          {projects.map((project) => (
            <div key={project.id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-slate-900">{project.title_en}</p>
                  <p className="text-sm text-slate-500">{project.slug}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() => {
                      setEditingId(project.id);
                      setForm({
                        title_ru: project.title_ru,
                        title_en: project.title_en,
                        summary_ru: project.summary_ru,
                        summary_en: project.summary_en,
                        description_ru: project.description_ru,
                        description_en: project.description_en,
                        stack: project.stack.join(", "),
                        preview_video_url: project.preview_video_url ?? "",
                        cover_image: project.cover_image ?? ""
                      });
                    }}
                  >
                    Edit
                  </Button>
                  <Button
                    size="xs"
                    color="red"
                    variant="light"
                    onClick={async () => {
                      if (!tokens?.access_token) {
                        return;
                      }
                      await deleteProject(project.id, tokens.access_token);
                      await loadProjects();
                    }}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </WindowFrame>

      <WindowFrame title={editingId ? "Edit project" : "Create project"} subtitle="Form">
        <Stack>
          <TextInput label="Title RU" value={form.title_ru} onChange={(e) => setForm({ ...form, title_ru: e.currentTarget.value })} />
          <TextInput label="Title EN" value={form.title_en} onChange={(e) => setForm({ ...form, title_en: e.currentTarget.value })} />
          <Textarea label="Summary RU" value={form.summary_ru} onChange={(e) => setForm({ ...form, summary_ru: e.currentTarget.value })} />
          <Textarea label="Summary EN" value={form.summary_en} onChange={(e) => setForm({ ...form, summary_en: e.currentTarget.value })} />
          <Textarea label="Description RU" minRows={4} value={form.description_ru} onChange={(e) => setForm({ ...form, description_ru: e.currentTarget.value })} />
          <Textarea label="Description EN" minRows={4} value={form.description_en} onChange={(e) => setForm({ ...form, description_en: e.currentTarget.value })} />
          <TextInput label="Stack" placeholder="FastAPI, Next.js, Redis" value={form.stack} onChange={(e) => setForm({ ...form, stack: e.currentTarget.value })} />
          <TextInput label="Preview video URL" value={form.preview_video_url} onChange={(e) => setForm({ ...form, preview_video_url: e.currentTarget.value })} />
          <TextInput label="Cover image URL" value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.currentTarget.value })} />
          <Button radius="xl" onClick={handleSave}>
            {editingId ? "Update project" : "Create project"}
          </Button>
        </Stack>
      </WindowFrame>
    </div>
  );
}
