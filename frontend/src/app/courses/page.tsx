import type { Metadata } from "next";
import Link from "next/link";
import { CourseCard } from "@/components/course-card";
import { getCourses } from "@/lib/api";

export const metadata: Metadata = {
  title: "Free online courses",
  description: "Browse recently checked free online courses that passed LearnLoot freshness, quality, and publication checks.",
  keywords: ["free online courses", "Udemy free courses", "free courses with ratings", "online learning deals"],
  alternates: { canonical: "/courses" },
  openGraph: { title: "Free online courses | LearnLoot", description: "Browse recently checked free courses that passed LearnLoot publication checks.", url: "/courses", type: "website" },
  twitter: { card: "summary_large_image", title: "Free online courses | LearnLoot", description: "Browse recently checked free courses that passed LearnLoot publication checks." },
};

type CoursesPageProps = { searchParams: Promise<Record<string, string | string[] | undefined>> };

export default async function CoursesPage({ searchParams }: CoursesPageProps) {
  const resolvedSearchParams = await searchParams;
  const q = typeof resolvedSearchParams.q === "string" ? resolvedSearchParams.q : "";
  const category = typeof resolvedSearchParams.category === "string" ? resolvedSearchParams.category : "";
  const courses = await getCourses({ limit: 48, q, category });

  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="public-eyebrow">Course catalog</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Recently checked free courses</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">Public courses must be active, recently checked, free in the latest price observation, and eligible under LearnLoot publication rules.</p>
        <Link className="public-link mt-3 inline-flex text-sm" href="/course-verification-policy">How LearnLoot verifies courses →</Link>
      </div>

      <div className="mt-8 border-y border-[color:var(--border)] py-5">
        <form className="grid gap-3 md:grid-cols-[1fr_auto_auto]" action="/courses">
          <label className="sr-only" htmlFor="course-search">Search courses</label>
          <input className="public-input min-w-0" defaultValue={q} id="course-search" name="q" placeholder="Search course, instructor, topic, category, or language" />
          {category ? <input name="category" type="hidden" value={category} /> : null}
          <button className="public-button public-button-primary" type="submit">Search</button>
          <Link className="public-button public-button-secondary" href="/courses/categories">Browse categories</Link>
        </form>
        {category ? (
          <div className="mt-3 flex items-center gap-2 text-sm text-[color:var(--muted)]">
            <span>Category filter: <strong className="text-[color:var(--foreground)]">{category}</strong></span>
            <Link className="public-link" href={q ? `/courses?q=${encodeURIComponent(q)}` : "/courses"}>Clear</Link>
          </div>
        ) : null}
      </div>

      <div className="mb-5 mt-7 flex items-center justify-between gap-4">
        <p className="text-sm text-[color:var(--muted)]">{courses.count} course{courses.count === 1 ? "" : "s"} shown</p>
      </div>

      {courses.results.length ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{courses.results.map((course) => <CourseCard course={course} key={course.id} />)}</div>
      ) : (
        <div className="public-card-muted p-10 text-center text-[color:var(--muted)]">No matching public courses found. Try another search or clear the category filter.</div>
      )}
    </main>
  );
}
