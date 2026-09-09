import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 items-center px-5 py-20">
      <div className="max-w-2xl">
        <p className="public-eyebrow">404</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">This page is not available</h1>
        <p className="mt-4 leading-7 text-[color:var(--muted)]">The page may have moved, a course may no longer be publicly eligible, or the link may be incorrect.</p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link className="public-button public-button-primary" href="/courses">Browse free courses</Link>
          <Link className="public-button public-button-secondary" href="/shop">Explore shopping guides</Link>
        </div>
      </div>
    </main>
  );
}
