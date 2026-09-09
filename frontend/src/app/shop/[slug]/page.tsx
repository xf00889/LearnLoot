/* eslint-disable @next/next/no-img-element */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { getShoppingPost } from "@/lib/api";
import { csvKeywords, getSiteUrl, splitEditorialLines } from "@/lib/seo";

function firstSearchValue(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function buildAffiliateOutboundUrl(
  outboundUrl: string,
  searchParams: Record<string, string | string[] | undefined>,
): string {
  const url = new URL(outboundUrl);
  const source = firstSearchValue(searchParams.source).trim();
  const campaign = firstSearchValue(searchParams.campaign).trim();
  url.searchParams.set("source", source || "shopping_page");
  if (campaign) url.searchParams.set("campaign", campaign);
  return url.toString();
}

type ShoppingDetailProps = {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: ShoppingDetailProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getShoppingPost(slug);
  if (!post) return { title: "Shopping guide not found", robots: { index: false, follow: false } };

  const image = post.seo.social_image_url || post.cover_image_url;
  return {
    title: post.seo.title || post.title,
    description: post.seo.description || post.excerpt,
    keywords: csvKeywords(post.seo.keywords),
    authors: [{ name: "LearnLoot" }],
    alternates: { canonical: post.url },
    openGraph: {
      type: "article",
      url: post.url,
      title: post.seo.title || post.title,
      description: post.seo.description || post.excerpt,
      publishedTime: post.published_at ?? undefined,
      modifiedTime: post.updated_at,
      images: image ? [{ url: image }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: post.seo.title || post.title,
      description: post.seo.description || post.excerpt,
      images: image ? [image] : undefined,
    },
    robots: { index: true, follow: true },
  };
}

export default async function ShoppingDetailPage({ params, searchParams }: ShoppingDetailProps) {
  const { slug } = await params;
  const resolvedSearchParams = await searchParams;
  const post = await getShoppingPost(slug);
  if (!post) notFound();

  const siteUrl = getSiteUrl();
  const articleJsonLd = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: post.title,
    description: post.seo.description || post.excerpt,
    url: post.url,
    datePublished: post.published_at,
    dateModified: post.updated_at,
    author: { "@type": "Organization", name: "LearnLoot", url: siteUrl },
    publisher: { "@type": "Organization", name: "LearnLoot", url: siteUrl },
    image: post.seo.social_image_url || post.cover_image_url || undefined,
  };
  const itemListJsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: post.title,
    numberOfItems: post.products.length,
    itemListElement: post.products.map((product) => ({
      "@type": "ListItem",
      position: product.position,
      name: product.name,
      url: `${post.url}#${product.slug}`,
    })),
  };
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: `${siteUrl}/` },
      { "@type": "ListItem", position: 2, name: "Shop & Deals", item: `${siteUrl}/shop` },
      { "@type": "ListItem", position: 3, name: post.title, item: post.url },
    ],
  };

  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-12">
      <JsonLd data={[articleJsonLd, itemListJsonLd, breadcrumbJsonLd]} />
      <Link className="text-sm font-bold text-[color:var(--accent)]" href="/shop">Back to shop & deals</Link>

      <article className="mt-6">
        <header className="rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-8 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-[0.24em] text-[color:var(--accent)]">{post.post_type_label}</p>
          <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">{post.title}</h1>
          {post.excerpt ? <p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">{post.excerpt}</p> : null}
          {post.cover_image_url ? <img alt={post.title} className="mt-7 aspect-[16/9] w-full rounded-3xl object-cover" src={post.cover_image_url} /> : null}
          <div className="mt-6 rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface)] p-4 text-sm leading-6 text-[color:var(--muted)]">
            <strong className="text-[color:var(--foreground)]">Affiliate disclosure:</strong> {post.affiliate_disclosure}
          </div>
        </header>

        {post.body ? <section className="cms-rich-content mx-auto max-w-3xl py-10 text-[color:var(--muted)]" dangerouslySetInnerHTML={{ __html: post.body }} /> : null}

        <section className="space-y-7" aria-label="Recommended products">
          {post.products.map((product) => {
            const outboundUrl = buildAffiliateOutboundUrl(product.outbound_url, resolvedSearchParams);
            const pros = splitEditorialLines(product.pros);
            const cons = splitEditorialLines(product.cons);
            return (
              <article className="scroll-mt-24 rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-6 shadow-sm" id={product.slug} key={product.id}>
                <div className="grid gap-6 md:grid-cols-[220px_1fr]">
                  <div>
                    {product.image_url ? <img alt={product.name} className="aspect-square w-full rounded-2xl object-cover" loading="lazy" src={product.image_url} /> : <div className="aspect-square rounded-2xl bg-[color:var(--surface)]" />}
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="rounded-full bg-[color:var(--surface)] px-3 py-1 text-sm font-black">#{product.position}</span>
                      {product.badge ? <span className="rounded-full bg-[color:var(--accent)] px-3 py-1 text-sm font-bold text-white">{product.badge}</span> : null}
                    </div>
                    <h2 className="mt-4 text-3xl font-black tracking-tight">{product.name}</h2>
                    {product.short_description ? <p className="mt-4 leading-7 text-[color:var(--muted)]">{product.short_description}</p> : null}

                    {product.displayed_price ? (
                      <p className="mt-5 text-xl font-black">
                        {product.currency} {product.displayed_price}
                        {product.original_price ? <span className="ml-3 text-sm font-normal text-[color:var(--muted)] line-through">{product.currency} {product.original_price}</span> : null}
                      </p>
                    ) : null}

                    {(pros.length || cons.length) ? (
                      <div className="mt-5 grid gap-4 sm:grid-cols-2">
                        {pros.length ? <div className="rounded-2xl bg-[color:var(--surface)] p-4"><h3 className="font-black">Pros</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[color:var(--muted)]">{pros.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
                        {cons.length ? <div className="rounded-2xl bg-[color:var(--surface)] p-4"><h3 className="font-black">Cons</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[color:var(--muted)]">{cons.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
                      </div>
                    ) : null}

                    <a className="mt-6 inline-flex rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white hover:bg-[color:var(--accent-strong)]" href={outboundUrl} rel="sponsored nofollow noopener noreferrer" target="_blank">View deal on Shopee</a>
                    <p className="mt-3 text-xs leading-5 text-[color:var(--muted)]">Price and availability may change. Confirm the current Shopee listing before purchasing.</p>
                  </div>
                </div>
              </article>
            );
          })}
        </section>
      </article>
    </main>
  );
}
