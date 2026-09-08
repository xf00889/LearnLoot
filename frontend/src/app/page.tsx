import Link from "next/link";
import { getCourses, type CourseSummary } from "@/lib/api";

function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <article className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3 text-xs font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
        <span>Free now</span>
        <span>{course.score}/100</span>
      </div>
      <h3 className="text-xl font-black tracking-tight">
        <Link href={`/courses/${course.provider.slug}/${course.slug}`}>
          {course.title}
        </Link>
      </h3>
      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        {course.instructor_name || course.provider.name}
      </p>
      <div className="mt-5 flex flex-wrap gap-2 text-sm text-[color:var(--muted)]">
        {course.rating ? <span>⭐ {course.rating}</span> : null}
        {course.review_count ? (
          <span>{course.review_count.toLocaleString()} reviews</span>
        ) : null}
        {course.duration_minutes ? <span>{course.duration_minutes} min</span> : null}
      </div>
    </article>
  );
}

export default async function Home() {
  const courses = await getCourses({ limit: 6 });
  const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();

  return (
    <main>
      <section className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-[color:var(--accent)]">
            Free course discovery
          </p>
          <h1 className="mt-5 text-5xl font-black tracking-tight sm:text-6xl">
            Find worthwhile free courses before the deal changes.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--muted)]">
            LearnLoot discovers public free-course opportunities, checks freshness
            and quality, and gives every shared deal a useful landing page before
            you continue to the provider.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white shadow-sm hover:bg-[color:var(--accent-strong)]"
              href="/courses"
            >
              Browse free courses
            </Link>
            {telegramChannelUrl ? (
              <a
                className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold text-[color:var(--foreground)] hover:bg-[color:var(--surface)]"
                href={telegramChannelUrl}
                rel="noopener noreferrer"
                target="_blank"
              >
                Follow the Telegram channel
              </a>
            ) : null}
          </div>
        </div>

        <aside className="rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface)] p-7 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
            Why LearnLoot
          </p>
          <div className="mt-6 grid gap-4">
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Discover</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                Public course listings are normalized into one searchable catalog.
              </p>
            </div>
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Verify</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                Only active, recently checked, currently free courses are public.
              </p>
            </div>
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Share</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">
                Telegram alerts point followers back to LearnLoot course pages.
              </p>
            </div>
          </div>
        </aside>
      </section>

      <section className="mx-auto w-full max-w-6xl px-5 pb-16">
        <div className="mb-7 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">
              Latest qualified deals
            </p>
            <h2 className="mt-3 text-3xl font-black tracking-tight">Ready to learn</h2>
          </div>
          <Link className="font-bold text-[color:var(--accent)]" href="/courses">
            View all →
          </Link>
        </div>

        {courses.results.length ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {courses.results.map((course) => (
              <CourseCard course={course} key={course.id} />
            ))}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">
            No qualified public deals are available right now. Check again after the
            next discovery run.
          </div>
        )}
      </section>

      <section
        className="mx-auto mb-16 w-full max-w-6xl rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface)] p-8"
        id="channel"
      >
        <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">
          Telegram Channel
        </p>
        <h2 className="mt-3 text-3xl font-black tracking-tight">
          Get new course alerts without losing the searchable website.
        </h2>
        <p className="mt-4 max-w-3xl leading-7 text-[color:var(--muted)]">
          Channel posts link back to LearnLoot first, so followers can check the
          course details and freshness before continuing to the provider.
        </p>
        {telegramChannelUrl ? (
          <a
            className="mt-6 inline-flex rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white"
            href={telegramChannelUrl}
            rel="noopener noreferrer"
            target="_blank"
          >
            Follow LearnLoot on Telegram
          </a>
        ) : (
          <p className="mt-6 text-sm text-[color:var(--muted)]">
            The public Telegram channel link will appear here once configured.
          </p>
        )}
      </section>
    </main>
  );
}
