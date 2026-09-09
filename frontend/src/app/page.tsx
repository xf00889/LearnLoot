import type { Metadata } from "next";
import Link from "next/link";
import {
  getCourses,
  getShoppingPosts,
  type CourseSummary,
  type ShoppingPostSummary,
} from "@/lib/api";

export const metadata: Metadata = {
  title: "Free courses and curated deals",
  description:
    "Discover recently checked free online courses plus independently curated product guides and deal roundups from LearnLoot.",
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
    title: "Free courses and curated deals | LearnLoot",
    description:
      "Recently checked free courses plus independently curated shopping guides and deal roundups.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Free courses and curated deals | LearnLoot",
    description:
      "Recently checked free courses plus independently curated shopping guides and deal roundups.",
  },
};

function CourseCard({ course }: { course: CourseSummary }) {
  return (
    <article className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between gap-3 text-xs font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
        <span>Free now</span>
        <span>{course.score}/100</span>
      </div>
      <h3 className="text-xl font-black tracking-tight">
        <Link href={`/courses/${course.provider.slug}/${course.slug}`}>{course.title}</Link>
      </h3>
      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        {course.instructor_name || course.provider.name}
      </p>
      <div className="mt-5 flex flex-wrap gap-2 text-sm text-[color:var(--muted)]">
        {course.rating ? <span>Rating {course.rating}</span> : null}
        {course.review_count ? <span>{course.review_count.toLocaleString()} reviews</span> : null}
        {course.duration_minutes ? <span>{course.duration_minutes} min</span> : null}
      </div>
    </article>
  );
}

function ShoppingCard({ post }: { post: ShoppingPostSummary }) {
  return (
    <article className="rounded-3xl border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-5 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
        {post.post_type_label}
      </p>
      <h3 className="mt-3 text-xl font-black tracking-tight">
        <Link href={`/shop/${post.slug}`}>{post.title}</Link>
      </h3>
      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        {post.excerpt || "An independently curated LearnLoot shopping guide."}
      </p>
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
      <section className="mx-auto grid w-full max-w-6xl gap-10 px-5 py-16 lg:grid-cols-[1.1fr_0.9fr] lg:py-24">
        <div>
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-[color:var(--accent)]">
            Learn smarter. Shop smarter.
          </p>
          <h1 className="mt-5 text-5xl font-black tracking-tight sm:text-6xl">
            Free courses and useful deals, organized in one place.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--muted)]">
            LearnLoot verifies public free-course opportunities and publishes original
            shopping guides, ranked product lists, and flash-deal roundups.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white" href="/courses">
              Browse free courses
            </Link>
            <Link className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold" href="/shop">
              Explore shop & deals
            </Link>
            {telegramChannelUrl ? (
              <a className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">
                Follow Telegram
              </a>
            ) : null}
          </div>
        </div>
        <aside className="rounded-[2rem] border border-[color:var(--border)] bg-[color:var(--surface)] p-7 shadow-sm">
          <p className="text-sm font-bold uppercase tracking-[0.22em] text-[color:var(--accent)]">
            What you get
          </p>
          <div className="mt-6 grid gap-4">
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Verified course deals</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">Only active, recently checked, currently free courses are public.</p>
            </div>
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Original shopping content</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">Top lists and deal articles are manually curated in the LearnLoot CMS.</p>
            </div>
            <div className="rounded-2xl bg-[color:var(--surface-strong)] p-5">
              <p className="font-black">Transparent affiliate links</p>
              <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">Shopping affiliate links are clearly disclosed and kept separate from course-provider links.</p>
            </div>
          </div>
        </aside>
      </section>

      <section className="mx-auto w-full max-w-6xl px-5 pb-16">
        <div className="mb-7 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Latest qualified course deals</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight">Ready to learn</h2>
          </div>
          <Link className="font-bold text-[color:var(--accent)]" href="/courses">View all</Link>
        </div>
        {courses.results.length ? (
          <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            {courses.results.map((course) => <CourseCard course={course} key={course.id} />)}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">No qualified public course deals are available right now.</div>
        )}
      </section>

      <section className="mx-auto w-full max-w-6xl px-5 pb-16">
        <div className="mb-7 flex items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">Shopping guides & deals</p>
            <h2 className="mt-3 text-3xl font-black tracking-tight">Curated by LearnLoot</h2>
          </div>
          <Link className="font-bold text-[color:var(--accent)]" href="/shop">Explore shop</Link>
        </div>
        {shopping.results.length ? (
          <div className="grid gap-5 md:grid-cols-3">
            {shopping.results.map((post) => <ShoppingCard post={post} key={post.id} />)}
          </div>
        ) : (
          <div className="rounded-3xl border border-dashed border-[color:var(--border)] p-10 text-center text-[color:var(--muted)]">Shopping guides will appear here after they are published from the CMS.</div>
        )}
      </section>
    </main>
  );
}
