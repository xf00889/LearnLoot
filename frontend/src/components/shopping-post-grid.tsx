/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import type { ShoppingPostSummary } from "@/lib/api";

export function ShoppingPostGrid({ posts }: { posts: ShoppingPostSummary[] }) {
  if (!posts.length) {
    return (
      <div className="rounded-3xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">
        No published shopping posts match this section yet.
      </div>
    );
  }

  return (
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {posts.map((post) => (
        <article
          className="overflow-hidden rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface-strong)] shadow-sm"
          key={post.id}
        >
          {post.cover_image_url ? (
            <img
              alt={post.title}
              className="aspect-[16/9] w-full object-cover"
              loading="lazy"
              src={post.cover_image_url}
            />
          ) : null}
          <div className="p-6">
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
              {post.post_type_label}
            </p>
            <h2 className="mt-3 text-2xl font-black tracking-tight">
              <Link href={`/shop/${post.slug}`}>{post.title}</Link>
            </h2>
            <p className="mt-3 leading-7 text-[color:var(--muted)]">
              {post.excerpt || "An independently curated LearnLoot shopping guide."}
            </p>
            <Link className="mt-5 inline-flex font-bold text-[color:var(--accent)]" href={`/shop/${post.slug}`}>
              Read guide
            </Link>
          </div>
        </article>
      ))}
    </div>
  );
}
