import type { Metadata } from "next";

import { getBlogPost } from "@/shared/api/client";
import { BlogPostPage } from "@/widgets/blog/ui/BlogPostPage";

export async function generateMetadata({
  params
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const { slug } = params;
  const post = await getBlogPost(slug);
  return {
    title: post.seo_title_en ?? post.title_en,
    description: post.seo_description_en ?? post.excerpt_en
  };
}

export default async function BlogPostRoute({
  params
}: {
  params: { slug: string };
}) {
  const { slug } = params;
  const post = await getBlogPost(slug);
  return <BlogPostPage post={post} />;
}
