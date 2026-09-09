import Link from "next/link";
import type { ReactNode } from "react";

export function PolicyPage({
  eyebrow,
  title,
  intro,
  children,
  updated = "September 10, 2026",
}: {
  eyebrow: string;
  title: string;
  intro: string;
  children: ReactNode;
  updated?: string;
}) {
  return (
    <main className="mx-auto w-full max-w-4xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="public-eyebrow">{eyebrow}</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.035em] sm:text-5xl">{title}</h1>
        <p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">{intro}</p>
        <p className="mt-4 text-sm text-[color:var(--muted)]">Last updated: {updated}</p>
      </div>

      <div className="public-card legal-copy mt-8 p-6 text-[color:var(--muted)] sm:p-8">
        {children}
      </div>

      <div className="mt-6 text-sm text-[color:var(--muted)]">
        Questions about this page? <Link className="public-link" href="/contact">Contact LearnLoot</Link>.
      </div>
    </main>
  );
}
