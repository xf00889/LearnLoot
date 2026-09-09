import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { JsonLd } from "@/components/json-ld";
import { getCourse } from "@/lib/api";
import { csvKeywords } from "@/lib/seo";

function firstSearchValue(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function buildAttributedOutboundUrl(
  outboundUrl: string,
  searchParams: Record<string, string | string[] | undefined>,
): string {
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
    openGraph: {
      title: course.seo.title || course.title,
      description: course.seo.description || course.description,
      url: course.url,
      type: "website",
      images: image ? [{ url: image }] : undefined,
    },
    twitter: {
      card: "summary_large_image",
      title: course.seo.title || course.title,
      description: course.seo.description || course.description,
      images: image ? [image] : undefined,
    },
    robots: { index: true, follow: true },
  };
}

export default async function CourseDetailPage({ params, searchParams }: CoursePageProps) {
  const { provider, slug } = await params;
  const resolvedSearchParams = await searchParams;
  const course = await getCourse(provider, slug);
  if (!course) notFound();

  const outboundUrl = buildAttributedOutboundUrl(course.outbound_url, resolvedSearchParams);
  const courseJsonLd = {
    "@context": "https://schema.org",
    "@type": "Course",
    name: course.title,
    description: course.description,
    url: course.url,
    provider: { "@type": "Organization", name: course.provider.name },
  };
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
    <main className="mx-auto w-full max-w-5xl px-5 py-12">
      <JsonLd data={[courseJsonLd, breadcrumbJsonLd]} />
      <Link className="text-sm font-bold text-[color:var(--accent)]" href="/courses">Back to courses</Link>

      <section className="mt-6 rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-8 shadow-sm">
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
          <span>Free now</span><span>•</span><span>{course.provider.name}</span><span>•</span><span>Score {course.score}/100</span>
        </div>
        <h1 className="mt-5 text-4xl font-black tracking-tight sm:text-5xl">{course.title}</h1>
        <p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">
          {course.description || "This free-course deal passed LearnLoot publication checks."}
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl bg-[color:var(--surface)] p-4"><p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Rating</p><p className="mt-1 text-2xl font-black">{course.rating ?? "N/A"}</p></div>
          <div className="rounded-2xl bg-[color:var(--surface)] p-4"><p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Reviews</p><p className="mt-1 text-2xl font-black">{course.review_count?.toLocaleString() ?? "N/A"}</p></div>
          <div className="rounded-2xl bg-[color:var(--surface)] p-4"><p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">Duration</p><p className="mt-1 text-2xl font-black">{course.duration_minutes ? `${course.duration_minutes} min` : "N/A"}</p></div>
        </div>

        <div className="mt-8 rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface)] p-5">
          <p className="font-bold">Instructor</p>
          <p className="mt-1 text-[color:var(--muted)]">{course.instructor_name || "Provider instructor details unavailable"}</p>
          <p className="mt-4 text-sm text-[color:var(--muted)]">Last checked: {course.last_checked_at ? new Date(course.last_checked_at).toLocaleString() : "Not available"}</p>
          <p className="mt-2 text-sm text-[color:var(--muted)]">Course availability can change after LearnLoot checks it. Confirm the current provider page before enrolling.</p>
          <p className="mt-2 text-sm text-[color:var(--muted)]">LearnLoot records a privacy-minimized outbound click when you continue, then sends you to the course provider&apos;s canonical page.</p>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <a className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white hover:bg-[color:var(--accent-strong)]" href={outboundUrl} rel="nofollow noopener noreferrer" target="_blank">Continue to free course</a>
          <Link className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold hover:bg-[color:var(--surface)]" href="/courses">Browse more deals</Link>
        </div>
      </section>
    </main>
  );
}
