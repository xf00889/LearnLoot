import type { Metadata } from "next";
import Link from "next/link";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = { title: "Flash deals", description: "Browse manually curated flash-deal and limited-time shopping pages published by LearnLoot.", alternates: { canonical: "/shop/flash-deals" } };

export default async function Page() {
  const posts = await getShoppingPosts({ limit: 48, type: "flash_deals" });
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <Link className="public-link text-sm" href="/shop">← Shop & Deals</Link>
      <p className="public-eyebrow mt-7">Limited-time offers</p>
      <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Flash deals</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Deal availability and prices can change. Always confirm the current merchant page before purchasing.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
