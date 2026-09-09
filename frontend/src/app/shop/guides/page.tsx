import type { Metadata } from "next";
import { ShoppingPostGrid } from "@/components/shopping-post-grid";
import { getShoppingPosts } from "@/lib/api";

export const metadata: Metadata = {
  title: "Buying guides",
  description: "Read LearnLoot buying guides designed to help compare products before visiting the merchant.",
  keywords: ["buying guides Philippines", "Shopee buying guide", "product comparison Philippines"],
  alternates: { canonical: "/shop/guides" },
  openGraph: { type: "website", url: "/shop/guides", title: "Buying guides | LearnLoot", description: "Read LearnLoot buying guides designed to help compare products before visiting the merchant." },
  twitter: { card: "summary_large_image", title: "Buying guides | LearnLoot", description: "Read LearnLoot buying guides designed to help compare products before visiting the merchant." },
};

export default async function GuidesPage() {
  const posts = await getShoppingPosts({ limit: 48, type: "buying_guide" });
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Editorial</p>
      <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Buying guides</h1>
      <p className="mb-8 mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">Original guides focused on useful comparisons, trade-offs, and purchase considerations.</p>
      <ShoppingPostGrid posts={posts.results} />
    </main>
  );
}
