import Link from "next/link";
import { getCourses } from "@/lib/api";

export const metadata = {
  title: "Free courses",
  description: "Browse currently free courses that passed LearnLoot publication checks.",
};

export default async function CoursesPage({ searchParams }: PageProps<"/courses">) {
  const resolvedSearchParams = await searchParams;
  const q = typeof resolvedSearchParams.q === "string" ? resolvedSearchParams.q : "";
  const courses = await getCourses({ limit: 48, q });

  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12">
      <div className="mb-8 max-w-3xl">
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">
          Course catalog
        </p>
        <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">
          Free courses that passed LearnLoot checks
        </h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">
          Public courses are active, recently checked, currently free in the latest
          price observation, and eligible under LearnLoot publication rules.
        </p>
      </div>

      <form className="mb-8 flex max-w-2xl gap-3" action="/courses">
        <input
          className="min-w-0 flex-1 rounded-full border border-[color:var(--border)] bg-[color:var(--surface-strong)] px-5 py-3 outline-none focus:ring-2 focus:ring-[color:var(--accent)]"
          defaultValue={q}
          name="q"
          placeholder="Search by course, instructor, or topic"
        />
        <button
          className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white"
          type="submit"
        >
          Search
        </button>
      </form>

      {courses.results.length ? (
        <div className="grid gap-5 md:grid-cols-2">
          {courses.results.map((course) => (
            <article
              className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-6"
              key={course.id}
            >
              <div className="flex items-center justify-between gap-4 text-sm">
                <span className="font-bold text-[color:var(--accent)]">Free now</span>
                <span className="text-[color:var(--muted)]">Score {course.score}/100</span>
              </div>
              <h2 className="mt-4 text-2xl font-black tracking-tight">
                <Link href={`/courses/${course.provider.slug}/${course.slug}`}>
                  {course.title}
                </Link>
              </h2>
              <p className="mt-3 text-[color:var(--muted)]">
                {course.instructor_name || course.provider.name}
              </p>
              <div className="mt-5 flex flex-wrap gap-3 text-sm text-[color:var(--muted)]">
                {course.rating ? <span>⭐ {course.rating}</span> : null}
                {course.review_count ? (
                  <span>{course.review_count.toLocaleString()} reviews</span>
                ) : null}
                {course.duration_minutes ? <span>{course.duration_minutes} min</span> : null}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-3xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">
          No matching public courses found.
        </div>
      )}
    </main>
  );
}
