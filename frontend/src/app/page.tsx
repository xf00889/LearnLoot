/* eslint-disable @next/next/no-img-element */
import type { Metadata } from "next";
import Link from "next/link";
import { CourseCard } from "@/components/course-card";
import {
  getCourses,
  getShoppingPosts,
  type ShoppingPostSummary,
} from "@/lib/api";

export const metadata: Metadata = {
  title: "Free courses and independent buying guides",
  description:
    "Discover recently checked free online courses plus independently edited product guides and deal roundups from LearnLoot.",
  keywords: [
    "free online courses",
    "Udemy free courses",
    "Shopee deals Philippines",
    "product guides Philippines",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: "/",
    title: "Free courses and independent buying guides | LearnLoot",
    description: "Recently checked free courses plus independently edited shopping guides and deal roundups.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Free courses and independent buying guides | LearnLoot",
    description: "Recently checked free courses plus independently edited shopping guides and deal roundups.",
  },
};

function ShoppingCard({ post }: { post: ShoppingPostSummary }) {
  return (
    <article className="public-card overflow-hidden">
      {post.cover_image_url ? <img alt={post.title} className="aspect-[16/9] w-full border-b border-[color:var(--border)] object-cover" loading="lazy" src={post.cover_image_url} /> : null}
      <div className="p-5">
        <div className="flex flex-wrap gap-2">
          <span className="public-badge public-badge-deal">{post.post_type_label}</span>
          {post.category ? <span className="public-badge bg-[color:var(--surface)] text-[color:var(--muted)]">{post.category.name}</span> : null}
        </div>
        <h3 className="mt-3 text-xl font-semibold tracking-[-0.025em]">
          <Link className="hover:text-[color:var(--accent)]" href={`/shop/${post.slug}`}>{post.title}</Link>
        </h3>
        <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">{post.excerpt || "An independently edited LearnLoot shopping guide."}</p>
        <Link className="public-link mt-4 inline-flex text-sm" href={`/shop/${post.slug}`}>Read guide →</Link>
      </div>
    </article>
  );
}

export default async function Home() {
  const [courses, shopping] = await Promise.all([
    getCourses({ limit: 6 }),
    getShoppingPosts({ limit: 3 }),
  ]);
  const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();

  return (
    <main>
      <section className="border-b border-[color:var(--border)] bg-[color:var(--surface-strong)]">
        <div className="mx-auto grid w-full max-w-7xl gap-10 px-5 py-16 lg:grid-cols-[1.2fr_0.8fr] lg:items-center lg:py-24">
          <div className="max-w-3xl">
            <p className="public-eyebrow">Free learning · Independent editorial</p>
            <h1 className="mt-4 text-5xl font-bold leading-[1.04] tracking-[-0.05em] sm:text-6xl">Learn more. Spend smarter.</h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--muted)]">
              LearnLoot surfaces recently checked free-course opportunities and publishes original shopping guides without mixing the two business models.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link className="public-button public-button-primary" href="/courses">Browse free courses</Link>
              <Link className="public-button public-button-secondary" href="/shop">Explore buying guides</Link>
              {telegramChannelUrl ? <a className="public-button public-button-secondary" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">Follow Telegram ↗</a> : null}
            </div>
          </div>

          <div className="public-card-muted grid gap-0 divide-y divide-[color:var(--border)]">
            <div className="p-5">
              <p className="text-sm font-semibold">Recently checked course opportunities</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">Public listings must remain active, free in the latest observation, and eligible under LearnLoot publication rules.</p>
            </div>
            <div className="p-5">
              <p className="text-sm font-semibold">Direct course-provider path</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">Udemy course links are kept separate from LearnLoot shopping monetization.</p>
            </div>
            <div className="p-5">
              <p className="text-sm font-semibold">Editorial shopping content</p>
              <p className="mt-1 text-sm leading-6 text-[color:var(--muted)]">Shopping articles are managed manually and disclose qualifying commission relationships.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-14">
        <div className="mb-6 flex items-end justify-between gap-4 border-b border-[color:var(--border)] pb-4">
          <div>
            <p className="public-eyebrow">Latest free courses</p>
            <h2 className="mt-2 text-3xl font-bold tracking-[-0.035em]">Ready to learn</h2>
          </div>
          <Link className="public-link text-sm" href="/courses">View all →</Link>
        </div>
        {courses.results.length ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">{courses.results.map((course) => <CourseCard course={course} key={course.id} />)}</div>
        ) : (
          <div className="public-card-muted p-10 text-center text-[color:var(--muted)]">No qualified public course opportunities are available right now.</div>
        )}
      </section>

      <section className="border-y border-[color:var(--border)] bg-[color:var(--surface-strong)]">
        <div className="mx-auto grid w-full max-w-7xl gap-8 px-5 py-12 lg:grid-cols-[0.7fr_1.3fr]">
          <div>
            <p className="public-eyebrow">How LearnLoot works</p>
            <h2 className="mt-2 text-3xl font-bold tracking-[-0.035em]">A simple trust model</h2>
            <p className="mt-4 leading-7 text-[color:var(--muted)]">Discovery, verification, publication, and rechecking are separate steps. Shopping editorial follows a separate workflow.</p>
            <Link className="public-link mt-5 inline-flex text-sm" href="/how-it-works">See the full process →</Link>
          </div>
          <ol className="grid gap-px overflow-hidden rounded-[6px] border border-[color:var(--border)] bg-[color:var(--border)] sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["01", "Discover", "Check permitted public sources."],
              ["02", "Verify", "Apply freshness, pricing, and quality rules."],
              ["03", "Publish", "Expose only eligible public records."],
              ["04", "Recheck", "Treat provider availability as changeable."],
            ].map(([number, title, copy]) => (
              <li className="bg-[color:var(--surface-strong)] p-5" key={number}>
                <span className="text-xs font-bold text-[color:var(--accent)]">{number}</span>
                <p className="mt-2 font-semibold">{title}</p>
                <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">{copy}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto w-full max-w-7xl px-5 py-14">
        <div className="mb-6 flex items-end justify-between gap-4 border-b border-[color:var(--border)] pb-4">
          <div>
            <p className="public-eyebrow">Shopping editorial</p>
            <h2 className="mt-2 text-3xl font-bold tracking-[-0.035em]">Guides, comparisons and deal roundups</h2>
          </div>
          <Link className="public-link text-sm" href="/shop">Explore shop →</Link>
        </div>
        {shopping.results.length ? (
          <div className="grid gap-5 md:grid-cols-3">{shopping.results.map((post) => <ShoppingCard post={post} key={post.id} />)}</div>
        ) : (
          <div className="public-card-muted p-10 text-center text-[color:var(--muted)]">Shopping guides will appear here after they are published from the CMS.</div>
        )}
      </section>
    </main>
  );
}
