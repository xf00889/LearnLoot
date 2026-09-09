import type { Metadata } from "next";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = {
  title: "Top 10 product lists",
  description: "Browse LearnLoot's independently curated Top 10 product lists and ranked buying roundups.",
  keywords: ["top 10 products Philippines", "best products Shopee Philippines", "product rankings Philippines"],
  alternates: { canonical: "/shop/top-10" },
  openGraph: { type: "website", url: "/shop/top-10", title: "Top 10 product lists | LearnLoot", description: "Browse LearnLoot's independently curated Top 10 product lists and ranked buying roundups." },
  twitter: { card: "summary_large_image", title: "Top 10 product lists | LearnLoot", description: "Browse LearnLoot's independently curated Top 10 product lists and ranked buying roundups." },
};

export default async function TopTenPage() {
  const posts = await getShoppingPosts({ limit: 48, type: "top_10" });
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Ranked lists</p>
      <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Top 10 product guides</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Manual rankings with original context, comparisons, pros, cons, and buying notes.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
