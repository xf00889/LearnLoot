import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] w-full max-w-3xl flex-col items-center justify-center px-5 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.25em] text-[color:var(--accent)]">
        Not found
      </p>
      <h1 className="mt-4 text-4xl font-black tracking-tight">
        This LearnLoot page is not public right now.
      </h1>
      <p className="mt-4 text-[color:var(--muted)]">
        A course deal may no longer be active, or a shopping article may still be
        a draft or archived in the CMS.
      </p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link className="rounded-full bg-[color:var(--accent)] px-6 py-3 font-bold text-white" href="/courses">
          Browse courses
        </Link>
        <Link className="rounded-full border border-[color:var(--border)] px-6 py-3 font-bold" href="/shop">
          Browse shop & deals
        </Link>
      </div>
    </main>
  );
}
