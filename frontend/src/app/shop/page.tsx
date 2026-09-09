import type { Metadata } from "next";
import Link from "next/link";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = {
  title: "Shopping guides and deals",
  description: "Browse LearnLoot's independently edited product roundups, Top 10 lists, buying guides, and flash-deal pages.",
  keywords: ["Shopee deals Philippines", "top products Philippines", "shopping guides Philippines", "flash deals Philippines"],
  alternates: { canonical: "/shop" },
  openGraph: { title: "Shopping guides and deals | LearnLoot", description: "Independent product roundups, ranked lists, and deal pages from LearnLoot.", url: "/shop", type: "website" },
  twitter: { card: "summary_large_image", title: "Shopping guides and deals | LearnLoot", description: "Independent product roundups, ranked lists, and deal pages from LearnLoot." },
};

type ShopPageProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const q = typeof params.q === "string" ? params.q : "";
  const posts = await getShoppingPosts({ limit: 48, q });
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="public-eyebrow">Shopping editorial</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Independent guides for smarter purchases</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">Product descriptions, rankings, comparisons, and recommendations are manually edited in the LearnLoot CMS rather than copied directly from merchant listings.</p>
        <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">Certain shopping links may generate a commission. Read the <Link className="public-link" href="/legal/affiliate-disclosure">affiliate disclosure</Link> and <Link className="public-link" href="/editorial-policy">editorial policy</Link>.</p>
      </div>

      <nav className="mt-8 flex flex-wrap gap-2 border-y border-[color:var(--border)] py-4" aria-label="Shopping sections">
        <Link className="public-button public-button-secondary text-sm" href="/shop/top-10">Top 10</Link>
        <Link className="public-button public-button-secondary text-sm" href="/shop/flash-deals">Flash deals</Link>
        <Link className="public-button public-button-secondary text-sm" href="/shop/guides">Buying guides</Link>
      </nav>

      <form className="my-7 grid max-w-2xl gap-3 sm:grid-cols-[1fr_auto]" action="/shop">
        <label className="sr-only" htmlFor="shop-search">Search shopping guides</label>
        <input className="public-input min-w-0" defaultValue={q} id="shop-search" name="q" placeholder="Search guides and products" />
        <button className="public-button public-button-primary" type="submit">Search</button>
      </form>

      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
