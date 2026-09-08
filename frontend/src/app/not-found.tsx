import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] w-full max-w-3xl flex-col items-center justify-center px-5 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">
        Not found
      </p>
      <h1 className="mt-4 text-4xl font-black tracking-tight">
        This course is not public right now.
      </h1>
      <p className="mt-4 text-[color:var(--muted)]">
        It may no longer be free, may be stale, may have been hidden, or may not
        have passed the latest LearnLoot publication checks.
      </p>
      <Link
        className="mt-8 rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white"
        href="/courses"
      >
        Browse active deals
      </Link>
    </main>
  );
}
