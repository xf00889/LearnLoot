/* eslint-disable @next/next/no-img-element */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { getShoppingPost } from "@/lib/api";
import { csvKeywords, getSiteUrl, splitEditorialLines } from "@/lib/seo";

function firstSearchValue(value: string | string[] | undefined): string { return Array.isArray(value) ? value[0] ?? "" : value ?? ""; }
function buildAffiliateOutboundUrl(outboundUrl: string, searchParams: Record<string, string | string[] | undefined>): string {
  const url = new URL(outboundUrl);
  const source = firstSearchValue(searchParams.source).trim();
  const campaign = firstSearchValue(searchParams.campaign).trim();
  url.searchParams.set("source", source || "shopping_page");
  if (campaign) url.searchParams.set("campaign", campaign);
  return url.toString();
}

type ShoppingDetailProps = { params: Promise<{ slug: string }>; searchParams: Promise<Record<string, string | string[] | undefined>> };

export async function generateMetadata({ params }: ShoppingDetailProps): Promise<Metadata> {
  const { slug } = await params;
  const post = await getShoppingPost(slug);
  if (!post) return { title: "Shopping guide not found", robots: { index: false, follow: false } };
  const image = post.seo.social_image_url || post.cover_image_url;
  return {
    title: post.seo.title || post.title,
    description: post.seo.description || post.excerpt,
    keywords: csvKeywords(post.seo.keywords), authors: [{ name: "LearnLoot" }], alternates: { canonical: post.url },
    openGraph: { type: "article", url: post.url, title: post.seo.title || post.title, description: post.seo.description || post.excerpt, publishedTime: post.published_at ?? undefined, modifiedTime: post.updated_at, images: image ? [{ url: image }] : undefined },
    twitter: { card: "summary_large_image", title: post.seo.title || post.title, description: post.seo.description || post.excerpt, images: image ? [image] : undefined }, robots: { index: true, follow: true },
  };
}

export default async function ShoppingDetailPage({ params, searchParams }: ShoppingDetailProps) {
  const { slug } = await params;
  const resolvedSearchParams = await searchParams;
  const post = await getShoppingPost(slug);
  if (!post) notFound();
  const siteUrl = getSiteUrl();
  const articleJsonLd = { "@context": "https://schema.org", "@type": "Article", headline: post.title, description: post.seo.description || post.excerpt, url: post.url, datePublished: post.published_at, dateModified: post.updated_at, author: { "@type": "Organization", name: "LearnLoot", url: siteUrl }, publisher: { "@type": "Organization", name: "LearnLoot", url: siteUrl }, image: post.seo.social_image_url || post.cover_image_url || undefined };
  const itemListJsonLd = { "@context": "https://schema.org", "@type": "ItemList", name: post.title, numberOfItems: post.products.length, itemListElement: post.products.map((product) => ({ "@type": "ListItem", position: product.position, name: product.name, url: `${post.url}#${product.slug}` })) };
  const breadcrumbJsonLd = { "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: [{ "@type": "ListItem", position: 1, name: "Home", item: `${siteUrl}/` }, { "@type": "ListItem", position: 2, name: "Shop & Deals", item: `${siteUrl}/shop` }, { "@type": "ListItem", position: 3, name: post.title, item: post.url }] };

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-10 sm:py-14">
      <JsonLd data={[articleJsonLd, itemListJsonLd, breadcrumbJsonLd]} />
      <Link className="public-link text-sm" href="/shop">← Shop & Deals</Link>
      <article className="mt-7">
        <header className="border-b border-[color:var(--border)] pb-8">
          <span className="public-badge public-badge-deal">{post.post_type_label}</span>
          <h1 className="mt-4 max-w-4xl text-4xl font-bold tracking-[-0.045em] sm:text-5xl">{post.title}</h1>
          {post.excerpt ? <p className="mt-5 max-w-3xl text-lg leading-8 text-[color:var(--muted)]">{post.excerpt}</p> : null}
          <div className="public-card-muted mt-6 max-w-3xl p-4 text-sm leading-6 text-[color:var(--muted)]"><strong className="text-[color:var(--foreground)]">Affiliate disclosure:</strong> {post.affiliate_disclosure} <Link className="public-link" href="/legal/affiliate-disclosure">Learn more</Link>.</div>
          {post.cover_image_url ? <img alt={post.title} className="mt-8 aspect-[16/9] w-full max-w-5xl rounded-[6px] border border-[color:var(--border)] object-cover" src={post.cover_image_url} /> : null}
        </header>

        {post.body ? <section className="cms-rich-content max-w-3xl py-9 leading-7 text-[color:var(--muted)]" dangerouslySetInnerHTML={{ __html: post.body }} /> : null}

        <section className="space-y-6" aria-label="Recommended products">
          {post.products.map((product) => {
            const outboundUrl = buildAffiliateOutboundUrl(product.outbound_url, resolvedSearchParams);
            const pros = splitEditorialLines(product.pros);
            const cons = splitEditorialLines(product.cons);
            return (
              <article className="public-card scroll-mt-24 p-5 sm:p-6" id={product.slug} key={product.id}>
                <div className="grid gap-6 md:grid-cols-[220px_1fr]">
                  <div>{product.image_url ? <img alt={product.name} className="aspect-square w-full rounded-[4px] border border-[color:var(--border)] object-cover" loading="lazy" src={product.image_url} /> : <div className="aspect-square rounded-[4px] bg-[color:var(--surface)]" />}</div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2"><span className="public-badge bg-[color:var(--surface)] text-[color:var(--muted)]">#{product.position}</span>{product.badge ? <span className="public-badge public-badge-deal">{product.badge}</span> : null}</div>
                    <h2 className="mt-3 text-2xl font-bold tracking-[-0.03em]">{product.name}</h2>
                    {(product.category || product.language) ? <p className="mt-2 text-sm text-[color:var(--muted)]">{[product.category?.name, product.language].filter(Boolean).join(" · ")}</p> : null}
                    {product.short_description ? <p className="mt-4 leading-7 text-[color:var(--muted)]">{product.short_description}</p> : null}
                    {product.content ? <div className="cms-rich-content mt-4 text-[color:var(--muted)]" dangerouslySetInnerHTML={{ __html: product.content }} /> : null}
                    {product.displayed_price ? <p className="mt-5 text-xl font-semibold">{product.currency} {product.displayed_price}{product.original_price ? <span className="ml-3 text-sm font-normal text-[color:var(--muted)] line-through">{product.currency} {product.original_price}</span> : null}</p> : null}
                    {(pros.length || cons.length) ? <div className="mt-5 grid gap-4 sm:grid-cols-2">{pros.length ? <div className="public-card-muted p-4"><h3 className="font-semibold">Pros</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[color:var(--muted)]">{pros.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}{cons.length ? <div className="public-card-muted p-4"><h3 className="font-semibold">Cons</h3><ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[color:var(--muted)]">{cons.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}</div> : null}
                    <a className="public-button public-button-primary mt-6" href={outboundUrl} rel="sponsored nofollow noopener noreferrer" target="_blank">View price on Shopee ↗</a>
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
