/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import type { ShoppingPostSummary } from "@/lib/api";

export function ShoppingPostGrid({ posts }: { posts: ShoppingPostSummary[] }) {
  if (!posts.length) {
    return <div className="public-card-muted p-10 text-center text-[color:var(--muted)]">No published shopping posts match this section yet.</div>;
  }
  return (
    <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
      {posts.map((post) => (
        <article className="public-card overflow-hidden" key={post.id}>
          {post.cover_image_url ? <img alt={post.title} className="aspect-[16/9] w-full border-b border-[color:var(--border)] object-cover" loading="lazy" src={post.cover_image_url} /> : null}
          <div className="p-5">
            <div className="flex flex-wrap gap-2">
              <span className="public-badge public-badge-deal">{post.post_type_label}</span>
              {post.category ? <span className="public-badge bg-[color:var(--surface)] text-[color:var(--muted)]">{post.category.name}</span> : null}
              {post.language ? <span className="text-xs text-[color:var(--muted)]">{post.language}</span> : null}
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-[-0.025em]"><Link className="hover:text-[color:var(--accent)]" href={`/shop/${post.slug}`}>{post.title}</Link></h2>
            <p className="mt-3 leading-7 text-[color:var(--muted)]">{post.excerpt || "An independently edited LearnLoot shopping guide."}</p>
            <Link className="public-link mt-5 inline-flex text-sm" href={`/shop/${post.slug}`}>Read guide →</Link>
          </div>
        </article>
      ))}
    </div>
  );
}
