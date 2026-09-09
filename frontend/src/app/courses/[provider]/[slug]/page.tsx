/* eslint-disable @next/next/no-img-element */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { getCourse } from "@/lib/api";
import { csvKeywords } from "@/lib/seo";

function firstSearchValue(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function buildAttributedOutboundUrl(outboundUrl: string, searchParams: Record<string, string | string[] | undefined>): string {
  const url = new URL(outboundUrl);
  const source = firstSearchValue(searchParams.source).trim();
  const campaign = firstSearchValue(searchParams.campaign).trim();
  url.searchParams.set("source", source || "course_page");
  if (campaign) url.searchParams.set("campaign", campaign);
  return url.toString();
}

type CoursePageProps = {
  params: Promise<{ provider: string; slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export async function generateMetadata({ params }: CoursePageProps): Promise<Metadata> {
  const { provider, slug } = await params;
  const course = await getCourse(provider, slug);
  if (!course) return { title: "Course not found", robots: { index: false, follow: false } };
  const image = course.seo.social_image_url || course.thumbnail_url;
  return {
    title: course.seo.title || course.title,
    description: course.seo.description || course.description,
    keywords: csvKeywords(course.seo.keywords),
    authors: [{ name: "LearnLoot" }],
    alternates: { canonical: course.url },
    openGraph: { title: course.seo.title || course.title, description: course.seo.description || course.description, url: course.url, type: "website", images: image ? [{ url: image }] : undefined },
    twitter: { card: "summary_large_image", title: course.seo.title || course.title, description: course.seo.description || course.description, images: image ? [image] : undefined },
    robots: { index: true, follow: true },
  };
}

export default async function CourseDetailPage({ params, searchParams }: CoursePageProps) {
  const { provider, slug } = await params;
  const resolvedSearchParams = await searchParams;
  const course = await getCourse(provider, slug);
  if (!course) notFound();

  const outboundUrl = buildAttributedOutboundUrl(course.outbound_url, resolvedSearchParams);
  const courseJsonLd = { "@context": "https://schema.org", "@type": "Course", name: course.title, description: course.description, url: course.url, provider: { "@type": "Organization", name: course.provider.name } };
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: new URL("/", course.url).toString() },
      { "@type": "ListItem", position: 2, name: "Courses", item: new URL("/courses", course.url).toString() },
      { "@type": "ListItem", position: 3, name: course.title, item: course.url },
    ],
  };

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-10 sm:py-14">
      <JsonLd data={[courseJsonLd, breadcrumbJsonLd]} />
      <nav className="mb-6 flex flex-wrap items-center gap-2 text-sm text-[color:var(--muted)]" aria-label="Breadcrumb">
        <Link className="public-link" href="/courses">Courses</Link>
        {course.category ? <><span>/</span><Link className="public-link" href={`/courses?category=${encodeURIComponent(course.category.slug)}`}>{course.category.name}</Link></> : null}
        <span>/</span><span className="line-clamp-1">{course.title}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-start">
        <article>
          <div className="flex flex-wrap items-center gap-2">
            <span className="public-badge public-badge-free">Free</span>
            <span className="text-sm text-[color:var(--muted)]">Course provided by {course.provider.name}</span>
          </div>
          <h1 className="mt-4 max-w-4xl text-4xl font-bold leading-tight tracking-[-0.045em] sm:text-5xl">{course.title}</h1>
          <p className="mt-4 text-sm text-[color:var(--muted)]">{[course.instructor_name, course.category?.name, course.language].filter(Boolean).join(" · ")}</p>
          {course.short_description ? <p className="mt-6 max-w-3xl text-lg leading-8 text-[color:var(--muted)]">{course.short_description}</p> : null}

          <section className="mt-8 border-y border-[color:var(--border)] py-6" aria-label="Course information">
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <div><p className="text-xs uppercase tracking-[0.12em] text-[color:var(--muted)]">Rating</p><p className="mt-1 text-xl font-semibold">{course.rating ?? "N/A"}</p></div>
              <div><p className="text-xs uppercase tracking-[0.12em] text-[color:var(--muted)]">Reviews</p><p className="mt-1 text-xl font-semibold">{course.review_count?.toLocaleString() ?? "N/A"}</p></div>
              <div><p className="text-xs uppercase tracking-[0.12em] text-[color:var(--muted)]">Duration</p><p className="mt-1 text-xl font-semibold">{course.duration_minutes ? `${course.duration_minutes} min` : "N/A"}</p></div>
              <div><p className="text-xs uppercase tracking-[0.12em] text-[color:var(--muted)]">LearnLoot score</p><p className="mt-1 text-xl font-semibold">{course.score}/100</p></div>
            </div>
          </section>

          <section className="mt-8">
            <h2 className="text-2xl font-bold tracking-[-0.03em]">About this course</h2>
            {course.description_html ? (
              <div className="cms-rich-content mt-5 max-w-3xl leading-7 text-[color:var(--muted)]" dangerouslySetInnerHTML={{ __html: course.description_html }} />
            ) : (
              <p className="mt-5 max-w-3xl leading-7 text-[color:var(--muted)]">{course.description || "This free-course opportunity passed LearnLoot publication checks."}</p>
            )}
          </section>

          <section className="public-card-muted mt-8 max-w-3xl p-5">
            <h2 className="font-semibold">Verification note</h2>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">Last checked: {course.last_checked_at ? new Date(course.last_checked_at).toLocaleString() : "Not available"}. Course availability can change after LearnLoot checks it, so confirm the current provider page before enrolling.</p>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">LearnLoot records a privacy-minimized outbound click when you continue, then sends you to the course provider&apos;s canonical page.</p>
            <Link className="public-link mt-3 inline-flex text-sm" href="/course-verification-policy">Read the course verification policy →</Link>
          </section>
        </article>

        <aside className="public-card overflow-hidden lg:sticky lg:top-24">
          {course.thumbnail_url ? <img alt={course.title} className="aspect-video w-full border-b border-[color:var(--border)] object-cover" src={course.thumbnail_url} /> : <div className="aspect-video bg-[color:var(--surface)]" />}
          <div className="p-5">
            <span className="public-badge public-badge-free">Currently free</span>
            <p className="mt-4 text-sm leading-6 text-[color:var(--muted)]">You will leave LearnLoot and continue to {course.provider.name} to confirm availability and enroll.</p>
            <a className="public-button public-button-primary mt-5 w-full" href={outboundUrl} rel="nofollow noopener noreferrer" target="_blank">Continue to free course ↗</a>
            <Link className="public-button public-button-secondary mt-2 w-full" href="/courses">Browse more courses</Link>
          </div>
        </aside>
      </div>
    </main>
  );
}
