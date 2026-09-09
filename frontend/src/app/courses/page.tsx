/* eslint-disable @next/next/no-img-element */
import type { Metadata } from "next";
import Link from "next/link";
import { getCourses } from "@/lib/api";

export const metadata: Metadata = {
  title: "Free online courses",
  description:
    "Browse recently checked free online courses that passed LearnLoot freshness, quality, and publication checks.",
  keywords: [
    "free online courses",
    "Udemy free courses",
    "free courses with ratings",
    "online learning deals",
  ],
  alternates: { canonical: "/courses" },
  openGraph: {
    title: "Free online courses | LearnLoot",
    description:
      "Browse recently checked free courses that passed LearnLoot publication checks.",
    url: "/courses",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Free online courses | LearnLoot",
    description:
      "Browse recently checked free courses that passed LearnLoot publication checks.",
  },
};

type CoursesPageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function CoursesPage({ searchParams }: CoursesPageProps) {
  const resolvedSearchParams = await searchParams;
  const q = typeof resolvedSearchParams.q === "string" ? resolvedSearchParams.q : "";
  const courses = await getCourses({ limit: 48, q });

  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="mb-8 max-w-3xl">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Course catalog</p>
        <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">Free courses that passed LearnLoot checks</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">Public courses are active, recently checked, currently free in the latest price observation, and eligible under LearnLoot publication rules.</p>
      </div>

      <form className="mb-8 flex max-w-2xl gap-3" action="/courses">
        <input className="min-w-0 flex-1 rounded-full border border-[color:var(--border)] bg-[color:var(--surface-strong)] px-5 py-3 outline-none focus:ring-2 focus:ring-[color:var(--accent)]" defaultValue={q} name="q" placeholder="Search by course, instructor, topic, category, or language" />
        <button className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white" type="submit">Search</button>
      </form>

      {courses.results.length ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {courses.results.map((course) => (
            <article className="overflow-hidden rounded-2xl border border-[color:var(--border)] bg-[color:var(--surface-strong)]" key={course.id}>
              <Link href={`/courses/${course.provider.slug}/${course.slug}`} className="block">
                {course.thumbnail_url ? (
                  <img alt={course.title} className="aspect-video w-full bg-[color:var(--surface)] object-cover" loading="lazy" src={course.thumbnail_url} />
                ) : (
                  <div className="aspect-video w-full bg-[color:var(--surface)]" aria-hidden="true" />
                )}
              </Link>
              <div className="p-5">
                <div className="flex items-center justify-between gap-4 text-sm"><span className="font-bold text-[color:var(--accent)]">Free now</span><span className="text-[color:var(--muted)]">Score {course.score}/100</span></div>
                <h2 className="mt-3 text-xl font-black tracking-tight"><Link href={`/courses/${course.provider.slug}/${course.slug}`}>{course.title}</Link></h2>
                {course.short_description ? <p className="mt-2 line-clamp-2 text-sm leading-6 text-[color:var(--muted)]">{course.short_description}</p> : null}
                <p className="mt-3 text-sm text-[color:var(--muted)]">{course.instructor_name || course.provider.name}</p>
                <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 text-xs text-[color:var(--muted)]">
                  {course.category ? <span>{course.category.name}</span> : null}
                  {course.language ? <span>{course.language}</span> : null}
                  {course.rating ? <span>Rating {course.rating}</span> : null}
                  {course.review_count ? <span>{course.review_count.toLocaleString()} reviews</span> : null}
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">No matching public courses found.</div>
      )}
    </main>
  );
}
