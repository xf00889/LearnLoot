import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getCourse } from "@/lib/api";

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
  if (campaign) {
    url.searchParams.set("campaign", campaign);
  }
  return url.toString();
}

export async function generateMetadata({
  params,
}: PageProps<"/courses/[provider]/[slug]">): Promise<Metadata> {
  const { provider, slug } = await params;
  const course = await getCourse(provider, slug);

  if (!course) {
    return {
      title: "Course not found",
    };
  }

  const description =
    course.description || `Free ${course.provider.name} course found by LearnLoot.`;

  return {
    title: course.title,
    description,
    alternates: {
      canonical: course.url,
    },
    openGraph: {
      title: course.title,
      description,
      url: course.url,
      type: "website",
      images: course.thumbnail_url ? [{ url: course.thumbnail_url }] : undefined,
    },
  };
}

export default async function CourseDetailPage({
  params,
  searchParams,
}: PageProps<"/courses/[provider]/[slug]">) {
  const { provider, slug } = await params;
  const resolvedSearchParams = await searchParams;
  const course = await getCourse(provider, slug);

  if (!course) {
    notFound();
  }

  const outboundUrl = buildAttributedOutboundUrl(
    course.outbound_url,
    resolvedSearchParams,
  );

  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-12">
      <Link className="text-sm font-bold text-[color:var(--accent)]" href="/courses">
        ← Back to courses
      </Link>

      <section className="mt-6 rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-8 shadow-sm">
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
          <span>Free now</span>
          <span>•</span>
          <span>{course.provider.name}</span>
          <span>•</span>
          <span>Score {course.score}/100</span>
        </div>

        <h1 className="mt-5 text-4xl font-black tracking-tight sm:text-5xl">
          {course.title}
        </h1>

        <p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">
          {course.description ||
            "This free-course deal passed LearnLoot publication checks."}
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <div className="rounded-2xl bg-[color:var(--surface)] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">
              Rating
            </p>
            <p className="mt-1 text-2xl font-black">{course.rating ?? "N/A"}</p>
          </div>
          <div className="rounded-2xl bg-[color:var(--surface)] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">
              Reviews
            </p>
            <p className="mt-1 text-2xl font-black">
              {course.review_count?.toLocaleString() ?? "N/A"}
            </p>
          </div>
          <div className="rounded-2xl bg-[color:var(--surface)] p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]">
              Duration
            </p>
            <p className="mt-1 text-2xl font-black">
              {course.duration_minutes ? `${course.duration_minutes} min` : "N/A"}
            </p>
          </div>
        </div>

        <div className="mt-8 rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface)] p-5">
          <p className="font-bold">Instructor</p>
          <p className="mt-1 text-[color:var(--muted)]">
            {course.instructor_name || "Provider instructor details unavailable"}
          </p>
          <p className="mt-4 text-sm text-[color:var(--muted)]">
            Last checked:{" "}
            {course.last_checked_at
              ? new Date(course.last_checked_at).toLocaleString()
              : "Not available"}
          </p>
          <p className="mt-2 text-sm text-[color:var(--muted)]">
            Course availability can change after LearnLoot checks it. Confirm the
            current provider page before enrolling.
          </p>
          <p className="mt-2 text-sm text-[color:var(--muted)]">
            LearnLoot records a privacy-minimized outbound click when you continue.
            {course.outbound_is_affiliate
              ? " This provider link is an affiliate link and LearnLoot may earn a commission at no extra cost to you."
              : " Affiliate tracking may be used only when an approved provider program is configured."}
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <a
            className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white hover:bg-[color:var(--accent-strong)]"
            href={outboundUrl}
            rel={
              course.outbound_is_affiliate
                ? "nofollow sponsored noopener noreferrer"
                : "nofollow noopener noreferrer"
            }
            target="_blank"
          >
            Continue to free course
          </a>
          <Link
            className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold hover:bg-[color:var(--surface)]"
            href="/courses"
          >
            Browse more deals
          </Link>
        </div>
      </section>
    </main>
  );
}
