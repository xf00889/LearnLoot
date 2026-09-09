import type { Metadata } from "next";
import Link from "next/link";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = { title: "Top 10 product lists", description: "Browse LearnLoot's independently edited Top 10 product lists and ranked buying roundups.", alternates: { canonical: "/shop/top-10" } };

export default async function Page() {
  const posts = await getShoppingPosts({ limit: 48, type: "top_10" });
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <Link className="public-link text-sm" href="/shop">← Shop & Deals</Link>
      <p className="public-eyebrow mt-7">Ranked lists</p>
      <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Top 10 product lists</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Manual rankings with original context, comparisons, pros, cons, and buying notes.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
