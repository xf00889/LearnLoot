import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Legal center", description: "LearnLoot privacy, terms, affiliate disclosure, and related trust policies.", alternates: { canonical: "/legal" } };

export default function LegalCenterPage() {
  const items = [
    ["Privacy policy", "/legal/privacy", "What LearnLoot processes for public visits, outbound clicks, staff sessions, and third-party links."],
    ["Terms of use", "/legal/terms", "The rules and limitations that apply when using LearnLoot and following third-party destinations."],
    ["Affiliate disclosure", "/legal/affiliate-disclosure", "How qualifying shopping links can generate a commission and how course links remain separate."],
    ["Editorial policy", "/editorial-policy", "Standards for manually edited shopping guides and rankings."],
    ["Course verification policy", "/course-verification-policy", "How free-course discovery, publication, and rechecking work."],
    ["Corrections policy", "/corrections-policy", "How to report material factual errors or stale public information."],
  ];
  return <main className="mx-auto w-full max-w-6xl px-5 py-12 sm:py-16"><div className="max-w-3xl"><p className="public-eyebrow">Legal & trust</p><h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">LearnLoot legal center</h1><p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">Policies for privacy, third-party links, editorial standards, course verification, corrections, and commission disclosures.</p></div><div className="mt-8 grid gap-4 md:grid-cols-2">{items.map(([title,href,copy]) => <Link className="public-card group p-5 hover:border-[color:var(--accent)]" href={href} key={href}><h2 className="font-semibold group-hover:text-[color:var(--accent)]">{title}</h2><p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">{copy}</p></Link>)}</div></main>;
}
