import type { Metadata } from "next";
import Link from "next/link";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = {
  title: "Shopping guides and deals",
  description:
    "Browse LearnLoot's independently written product roundups, Top 10 lists, buying guides, and flash-deal pages.",
  keywords: [
    "Shopee deals Philippines",
    "top products Philippines",
    "shopping guides Philippines",
    "flash deals Philippines",
  ],
  alternates: { canonical: "/shop" },
  openGraph: {
    title: "Shopping guides and deals | LearnLoot",
    description: "Independent product roundups, ranked lists, and deal pages from LearnLoot.",
    url: "/shop",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Shopping guides and deals | LearnLoot",
    description: "Independent product roundups, ranked lists, and deal pages from LearnLoot.",
  },
};

type ShopPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const q = typeof params.q === "string" ? params.q : "";
  const posts = await getShoppingPosts({ limit: 48, q });

  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="max-w-3xl">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Shop & deals</p>
        <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Independent guides for smarter purchases</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">
          LearnLoot shopping pages are manually edited. Product descriptions, rankings, and recommendations should add original value rather than copying merchant listings.
        </p>
        <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
          Some shopping links are affiliate links. LearnLoot may earn a commission from qualifying purchases at no additional cost to you.
        </p>
      </div>

      <nav className="mt-8 flex flex-wrap gap-3" aria-label="Shopping sections">
        <Link className="rounded-full border border-[color:var(--border)] px-4 py-2 font-bold" href="/shop/top-10">Top 10</Link>
        <Link className="rounded-full border border-[color:var(--border)] px-4 py-2 font-bold" href="/shop/flash-deals">Flash deals</Link>
        <Link className="rounded-full border border-[color:var(--border)] px-4 py-2 font-bold" href="/shop/guides">Buying guides</Link>
      </nav>

      <form className="my-8 flex max-w-2xl gap-3" action="/shop">
        <input className="min-w-0 flex-1 rounded-full border border-[color:var(--border)] bg-[color:var(--surface-strong)] px-5 py-3" defaultValue={q} name="q" placeholder="Search guides and products" />
        <button className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white" type="submit">Search</button>
      </form>

      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
