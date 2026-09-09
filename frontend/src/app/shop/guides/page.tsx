import type { Metadata } from "next";
import Link from "next/link";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = { title: "Buying guides", description: "Read LearnLoot buying guides designed to help compare products before visiting the merchant.", alternates: { canonical: "/shop/guides" } };

export default async function Page() {
  const posts = await getShoppingPosts({ limit: 48, type: "buying_guide" });
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <Link className="public-link text-sm" href="/shop">← Shop & Deals</Link>
      <p className="public-eyebrow mt-7">Editorial</p>
      <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Buying guides</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Original guides focused on useful comparisons, trade-offs, and purchase considerations.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
