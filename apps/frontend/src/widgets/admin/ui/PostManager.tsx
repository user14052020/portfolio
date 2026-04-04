"use client";

import { Button, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createBlogPost, deleteBlogPost, getBlogPosts, updateBlogPost } from "@/shared/api/client";
import type { BlogPost, BlogPostType } from "@/shared/api/types";
import { WindowFrame } from "@/shared/ui/WindowFrame";

type PostForm = {
  title_ru: string;
  title_en: string;
  excerpt_ru: string;
  excerpt_en: string;
  content_ru: string;
  content_en: string;
  tags: string;
  cover_image: string;
  video_url: string;
  post_type: BlogPostType;
};

const emptyForm: PostForm = {
  title_ru: "",
  title_en: "",
  excerpt_ru: "",
  excerpt_en: "",
  content_ru: "",
  content_en: "",
  tags: "",
  cover_image: "",
  video_url: "",
  post_type: "article"
};

export function PostManager() {
  const { tokens } = useAdminAuth();
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<PostForm>(emptyForm);

  const loadPosts = useCallback(async () => {
    if (!tokens?.access_token) {
      return;
    }
    const items = await getBlogPosts({ includeDrafts: true }, tokens.access_token);
    setPosts(items);
  }, [tokens?.access_token]);

  useEffect(() => {
    void loadPosts();
  }, [loadPosts]);

  const handleSave = async () => {
    if (!tokens?.access_token) {
      return;
    }
    const payload = {
      ...form,
      tags: form.tags.split(",").map((item) => item.trim()).filter(Boolean)
    };
    if (editingId) {
      await updateBlogPost(editingId, payload, tokens.access_token);
    } else {
      await createBlogPost(payload, tokens.access_token);
    }
    setForm(emptyForm);
    setEditingId(null);
    await loadPosts();
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <WindowFrame title="Posts" subtitle="CRUD">
        <div className="space-y-3">
          {posts.map((post) => (
            <div key={post.id} className="rounded-[20px] border border-slate-200 bg-slate-50 p-4">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-medium text-slate-900">{post.title_en}</p>
                  <p className="text-sm text-slate-500">{post.post_type}</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() => {
                      setEditingId(post.id);
                      setForm({
                        title_ru: post.title_ru,
                        title_en: post.title_en,
                        excerpt_ru: post.excerpt_ru,
                        excerpt_en: post.excerpt_en,
                        content_ru: post.content_ru,
                        content_en: post.content_en,
                        tags: post.tags.join(", "),
                        cover_image: post.cover_image ?? "",
                        video_url: post.video_url ?? "",
                        post_type: post.post_type
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
                      await deleteBlogPost(post.id, tokens.access_token);
                      await loadPosts();
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

      <WindowFrame title={editingId ? "Edit post" : "Create post"} subtitle="Form">
        <Stack>
          <TextInput label="Title RU" value={form.title_ru} onChange={(e) => setForm({ ...form, title_ru: e.currentTarget.value })} />
          <TextInput label="Title EN" value={form.title_en} onChange={(e) => setForm({ ...form, title_en: e.currentTarget.value })} />
          <Textarea label="Excerpt RU" value={form.excerpt_ru} onChange={(e) => setForm({ ...form, excerpt_ru: e.currentTarget.value })} />
          <Textarea label="Excerpt EN" value={form.excerpt_en} onChange={(e) => setForm({ ...form, excerpt_en: e.currentTarget.value })} />
          <Textarea label="Content RU" minRows={5} value={form.content_ru} onChange={(e) => setForm({ ...form, content_ru: e.currentTarget.value })} />
          <Textarea label="Content EN" minRows={5} value={form.content_en} onChange={(e) => setForm({ ...form, content_en: e.currentTarget.value })} />
          <TextInput label="Tags" placeholder="ai, architecture, motion" value={form.tags} onChange={(e) => setForm({ ...form, tags: e.currentTarget.value })} />
          <Select
            label="Post type"
            data={[
              { label: "Article", value: "article" },
              { label: "Video", value: "video" }
            ]}
            value={form.post_type}
            onChange={(value) => setForm({ ...form, post_type: (value as BlogPostType | null) ?? "article" })}
          />
          <TextInput label="Cover image URL" value={form.cover_image} onChange={(e) => setForm({ ...form, cover_image: e.currentTarget.value })} />
          <TextInput label="Video URL" value={form.video_url} onChange={(e) => setForm({ ...form, video_url: e.currentTarget.value })} />
          <Button radius="xl" onClick={handleSave}>
            {editingId ? "Update post" : "Create post"}
          </Button>
        </Stack>
      </WindowFrame>
    </div>
  );
}
