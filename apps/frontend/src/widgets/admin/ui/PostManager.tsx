"use client";

import { Select, Textarea, TextInput } from "@mantine/core";
import { useCallback, useEffect, useState } from "react";

import { useAdminAuth } from "@/features/admin-auth/model/useAdminAuth";
import { createBlogPost, deleteBlogPost, getBlogPosts, updateBlogPost } from "@/shared/api/browser-client";
import type { BlogPost, BlogPostType } from "@/shared/api/types";
import { PillBadge } from "@/shared/ui/PillBadge";
import { SectionHeader } from "@/shared/ui/SectionHeader";
import { SoftButton } from "@/shared/ui/SoftButton";
import { SurfaceCard } from "@/shared/ui/SurfaceCard";

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
  post_type: "article",
};

const POST_TYPE_OPTIONS: Array<{ label: string; value: BlogPostType }> = [
  { label: "Article", value: "article" },
  { label: "Video", value: "video" },
];

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildPostPayload(form: PostForm): Partial<BlogPost> {
  return {
    ...form,
    tags: parseCommaList(form.tags),
  };
}

function buildPostForm(post: BlogPost): PostForm {
  return {
    title_ru: post.title_ru,
    title_en: post.title_en,
    excerpt_ru: post.excerpt_ru,
    excerpt_en: post.excerpt_en,
    content_ru: post.content_ru,
    content_en: post.content_en,
    tags: post.tags.join(", "),
    cover_image: post.cover_image ?? "",
    video_url: post.video_url ?? "",
    post_type: post.post_type,
  };
}

export function PostManager() {
  const { tokens } = useAdminAuth();
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<PostForm>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  const loadPosts = useCallback(async () => {
    if (!tokens?.access_token) {
      return;
    }
    try {
      const items = await getBlogPosts({ includeDrafts: true }, tokens.access_token);
      setPosts(items);
      setError(null);
    } catch (nextError) {
      setPosts([]);
      setError(nextError instanceof Error ? nextError.message : "Failed to load posts");
    }
  }, [tokens?.access_token]);

  useEffect(() => {
    void loadPosts();
  }, [loadPosts]);

  function handleEdit(post: BlogPost) {
    setEditingId(post.id);
    setForm(buildPostForm(post));
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
      const payload = buildPostPayload(form);
      if (editingId) {
        await updateBlogPost(editingId, payload, tokens.access_token);
      } else {
        await createBlogPost(payload, tokens.access_token);
      }
      resetForm();
      await loadPosts();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to save post");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleDelete(postId: number) {
    if (!tokens?.access_token) {
      return;
    }
    setDeletingId(postId);
    try {
      await deleteBlogPost(postId, tokens.access_token);
      if (editingId === postId) {
        resetForm();
      }
      await loadPosts();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Failed to delete post");
    } finally {
      setDeletingId(null);
    }
  }

  if (!tokens?.access_token) {
    return (
      <SurfaceCard variant="soft">
        <PostManagerHeader count={0} />
        <p className="mt-4 text-sm text-[var(--text-secondary)]">
          Sign in as admin to create, edit, and delete writing entries.
        </p>
      </SurfaceCard>
    );
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
      <SurfaceCard variant="elevated" header={<PostManagerHeader count={posts.length} />}>
        <div className="space-y-3">
          {posts.map((post) => (
            <PostListCard
              key={post.id}
              post={post}
              isEditing={editingId === post.id}
              isDeleting={deletingId === post.id}
              onEdit={() => handleEdit(post)}
              onDelete={() => void handleDelete(post.id)}
            />
          ))}
          {posts.length === 0 ? (
            <div className="rounded-[24px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5 text-sm text-[var(--text-secondary)]">
              No posts yet.
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
            eyebrow="Writing form"
            title={editingId ? "Edit post" : "Create post"}
            description="Maintain bilingual articles and videos for the public content surface."
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
              label="Excerpt RU"
              value={form.excerpt_ru}
              onChange={(event) => setForm({ ...form, excerpt_ru: event.currentTarget.value })}
            />
            <Textarea
              label="Excerpt EN"
              value={form.excerpt_en}
              onChange={(event) => setForm({ ...form, excerpt_en: event.currentTarget.value })}
            />
          </div>
          <Textarea
            label="Content RU"
            minRows={5}
            value={form.content_ru}
            onChange={(event) => setForm({ ...form, content_ru: event.currentTarget.value })}
          />
          <Textarea
            label="Content EN"
            minRows={5}
            value={form.content_en}
            onChange={(event) => setForm({ ...form, content_en: event.currentTarget.value })}
          />
          <div className="grid gap-4 md:grid-cols-2">
            <TextInput
              label="Tags"
              placeholder="ai, architecture, motion"
              value={form.tags}
              onChange={(event) => setForm({ ...form, tags: event.currentTarget.value })}
            />
            <Select
              label="Post type"
              data={POST_TYPE_OPTIONS}
              value={form.post_type}
              onChange={(value) => setForm({ ...form, post_type: (value as BlogPostType | null) ?? "article" })}
            />
            <TextInput
              label="Cover image URL"
              value={form.cover_image}
              onChange={(event) => setForm({ ...form, cover_image: event.currentTarget.value })}
            />
            <TextInput
              label="Video URL"
              value={form.video_url}
              onChange={(event) => setForm({ ...form, video_url: event.currentTarget.value })}
            />
          </div>
          <SoftButton tone="dark" onClick={() => void handleSave()} disabled={isSaving}>
            {isSaving ? "Saving..." : editingId ? "Update post" : "Create post"}
          </SoftButton>
        </div>
      </SurfaceCard>
    </div>
  );
}

function PostManagerHeader({ count }: { count: number }) {
  return (
    <SectionHeader
      eyebrow="Content CMS"
      title="Posts"
      description="Create and maintain articles and videos for the public writing section."
      action={
        <PillBadge tone="dark">
          {count} total
        </PillBadge>
      }
    />
  );
}

function PostListCard({
  post,
  isEditing,
  isDeleting,
  onEdit,
  onDelete,
}: {
  post: BlogPost;
  isEditing: boolean;
  isDeleting: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <article className="rounded-[26px] border border-[var(--border-soft)] bg-[var(--surface-secondary)] p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <PillBadge tone={post.is_published ? "success" : "warning"} size="sm">
              {post.is_published ? "published" : "draft"}
            </PillBadge>
            <PillBadge tone={post.post_type === "video" ? "lilac" : "accent"} size="sm">
              {post.post_type}
            </PillBadge>
            {isEditing ? (
              <PillBadge tone="dark" size="sm">
                editing
              </PillBadge>
            ) : null}
          </div>
          <div>
            <p className="font-semibold text-[var(--text-primary)]">{post.title_en}</p>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">{post.slug}</p>
          </div>
          <p className="line-clamp-2 text-sm leading-6 text-[var(--text-secondary)]">{post.excerpt_en}</p>
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
