import type { Metadata } from "next";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = {
  title: "Flash deals",
  description: "Browse manually curated flash-deal and limited-time shopping pages published by LearnLoot.",
  keywords: ["flash deals Philippines", "Shopee flash deals", "limited time deals Philippines"],
  alternates: { canonical: "/shop/flash-deals" },
  openGraph: { type: "website", url: "/shop/flash-deals", title: "Flash deals | LearnLoot", description: "Browse manually curated flash-deal and limited-time shopping pages published by LearnLoot." },
  twitter: { card: "summary_large_image", title: "Flash deals | LearnLoot", description: "Browse manually curated flash-deal and limited-time shopping pages published by LearnLoot." },
};

export default async function FlashDealsPage() {
  const posts = await getShoppingPosts({ limit: 48, type: "flash_deals" });
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Limited-time offers</p>
      <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Flash deals</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Deal availability and prices can change. Always confirm the current merchant page before purchasing.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
