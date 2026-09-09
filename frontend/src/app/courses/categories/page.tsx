import type { Metadata } from "next";
import Link from "next/link";
import { getCourseCategories } from "@/lib/api";

export const metadata: Metadata = {
  title: "Course categories",
  description: "Browse categories represented by currently public, recently checked free courses on LearnLoot.",
  alternates: { canonical: "/courses/categories" },
};

export default async function CourseCategoriesPage() {
  const payload = await getCourseCategories();
  return (
    <main className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="public-eyebrow">Course categories</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Browse the current public catalog by category</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">Categories are assigned manually in the LearnLoot CMS. Automated Udemy discovery does not create or guess LearnLoot categories.</p>
      </div>

      {payload.results.length ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {payload.results.map((category) => (
            <Link className="public-card group p-5 transition-colors hover:border-[color:var(--accent)]" href={`/courses?category=${encodeURIComponent(category.slug)}`} key={category.slug}>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold group-hover:text-[color:var(--accent)]">{category.name}</h2>
                  <p className="mt-2 text-sm text-[color:var(--muted)]">{category.count} public course{category.count === 1 ? "" : "s"}</p>
                </div>
                <span className="text-[color:var(--accent)]" aria-hidden="true">→</span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="public-card-muted mt-8 p-10 text-center text-[color:var(--muted)]">No manually categorized public courses are available yet.</div>
      )}
    </main>
  );
}
