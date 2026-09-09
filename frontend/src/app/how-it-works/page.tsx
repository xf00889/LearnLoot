import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "How LearnLoot works", description: "Understand LearnLoot's course discovery, verification, publication, recheck, and shopping editorial workflows.", alternates: { canonical: "/how-it-works" } };

const courseSteps = [
  ["01", "Discover", "LearnLoot checks permitted public course sources through provider-isolated discovery connectors."],
  ["02", "Normalize", "Provider data is converted into a stable internal course record while human CMS overrides stay separate."],
  ["03", "Verify", "Freshness, free-price observations, quality signals, provider status, and publication eligibility are checked."],
  ["04", "Publish", "Only records that remain eligible and currently free are exposed on public course pages."],
  ["05", "Recheck", "Availability can change, so later discovery runs and price observations can remove stale or no-longer-free records from public results."],
];

export default function HowItWorksPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl"><p className="public-eyebrow">How it works</p><h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Two workflows, deliberately separated</h1><p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">Course discovery is automation-assisted and compliance-first. Shopping content is editorial and manually managed. LearnLoot keeps those systems separate.</p></div>
      <section className="mt-10"><h2 className="text-2xl font-bold">Course workflow</h2><ol className="mt-5 grid gap-px overflow-hidden rounded-[6px] border border-[color:var(--border)] bg-[color:var(--border)] lg:grid-cols-5">{courseSteps.map(([number,title,copy]) => <li className="bg-[color:var(--surface-strong)] p-5" key={number}><span className="text-xs font-bold text-[color:var(--accent)]">{number}</span><h3 className="mt-2 font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">{copy}</p></li>)}</ol><Link className="public-link mt-4 inline-flex text-sm" href="/course-verification-policy">Detailed verification policy →</Link></section>
      <section className="mt-12 border-t border-[color:var(--border)] pt-9"><h2 className="text-2xl font-bold">Shopping editorial workflow</h2><div className="mt-5 grid gap-4 md:grid-cols-4">{[["Research","Choose a useful editorial angle and products to discuss."],["Edit","Write original context, comparisons, pros, cons, and buying notes."],["Disclose","Keep commission relationships visible near relevant shopping content."],["Publish","Send visitors through LearnLoot's controlled shopping redirect to the merchant."]].map(([title,copy]) => <div className="public-card p-5" key={title}><h3 className="font-semibold">{title}</h3><p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">{copy}</p></div>)}</div><Link className="public-link mt-4 inline-flex text-sm" href="/editorial-policy">Editorial policy →</Link></section>
    </main>
  );
}
