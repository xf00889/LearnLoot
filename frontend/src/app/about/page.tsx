import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "About", description: "Learn what LearnLoot does, how free-course discovery differs from shopping editorial, and how the platform is designed.", alternates: { canonical: "/about" } };

export default function AboutPage() {
  return (
    <main className="mx-auto w-full max-w-6xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl">
        <p className="public-eyebrow">About LearnLoot</p>
        <h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">A clearer way to discover free learning and useful buying information</h1>
        <p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">LearnLoot is an independent discovery and editorial platform. It surfaces eligible free-course opportunities and separately publishes manually edited shopping guides.</p>
      </div>
      <div className="mt-10 grid gap-5 md:grid-cols-2">
        <section className="public-card p-6"><span className="public-badge public-badge-free">Learning</span><h2 className="mt-4 text-2xl font-bold">Course discovery</h2><p className="mt-3 leading-7 text-[color:var(--muted)]">Course records originate from permitted public discovery sources, pass publication checks, and link visitors through a controlled redirect to the provider&apos;s canonical course page. Udemy course links are non-affiliate.</p><Link className="public-link mt-4 inline-flex" href="/course-verification-policy">Verification policy →</Link></section>
        <section className="public-card p-6"><span className="public-badge public-badge-deal">Editorial</span><h2 className="mt-4 text-2xl font-bold">Shopping guides</h2><p className="mt-3 leading-7 text-[color:var(--muted)]">Shopping posts and product recommendations are managed manually in the LearnLoot CMS. Certain outbound shopping destinations may be commission-earning links and are disclosed accordingly.</p><Link className="public-link mt-4 inline-flex" href="/editorial-policy">Editorial policy →</Link></section>
      </div>
      <section className="mt-10 border-t border-[color:var(--border)] pt-8"><h2 className="text-2xl font-bold">What LearnLoot is not</h2><div className="mt-4 grid gap-4 text-sm leading-6 text-[color:var(--muted)] sm:grid-cols-3"><p>LearnLoot is not the course provider and does not deliver third-party course content.</p><p>LearnLoot is not the merchant and does not process purchases for products linked from editorial pages.</p><p>LearnLoot does not guarantee that a course stays free or that a merchant price remains unchanged after the last check.</p></div></section>
    </main>
  );
}
