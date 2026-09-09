/* eslint-disable @next/next/no-img-element */
import Link from "next/link";
import type { CourseSummary } from "@/lib/api";

function checkedLabel(value: string | null): string {
  if (!value) return "Recently checked";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently checked";
  return `Checked ${new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date)}`;
}

export function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <article className="public-card overflow-hidden">
      <Link className="block border-b border-[color:var(--border)] bg-[color:var(--surface)]" href={`/courses/${course.provider.slug}/${course.slug}`}>
        {course.thumbnail_url ? (
          <img alt={course.title} className="aspect-video w-full object-cover" loading="lazy" src={course.thumbnail_url} />
        ) : (
          <div className="flex aspect-video w-full items-center justify-center text-sm text-[color:var(--muted)]" aria-hidden="true">LearnLoot course</div>
        )}
      </Link>
      <div className="p-5">
        <div className="flex items-center justify-between gap-3">
          <span className="public-badge public-badge-free">Free</span>
          <span className="text-xs text-[color:var(--muted)]">{checkedLabel(course.last_checked_at)}</span>
        </div>
        <h2 className="mt-3 text-lg font-semibold leading-6 tracking-[-0.02em]">
          <Link className="hover:text-[color:var(--accent)]" href={`/courses/${course.provider.slug}/${course.slug}`}>{course.title}</Link>
        </h2>
        {course.short_description ? <p className="mt-2 line-clamp-2 text-sm leading-6 text-[color:var(--muted)]">{course.short_description}</p> : null}
        <p className="mt-3 text-sm text-[color:var(--muted)]">{course.instructor_name || course.provider.name}</p>
        <div className="mt-4 flex flex-wrap gap-x-3 gap-y-1 border-t border-[color:var(--border)] pt-3 text-xs text-[color:var(--muted)]">
          {course.category ? <span>{course.category.name}</span> : null}
          {course.language ? <span>{course.language}</span> : null}
          {course.rating ? <span>★ {course.rating}</span> : null}
          {course.review_count ? <span>{course.review_count.toLocaleString()} reviews</span> : null}
        </div>
      </div>
    </article>
  );
}
