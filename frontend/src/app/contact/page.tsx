import type { Metadata } from "next";

export const metadata: Metadata = { title: "Contact", description: "Contact LearnLoot about corrections, privacy, editorial questions, or site issues.", alternates: { canonical: "/contact" } };

export default function ContactPage() {
  const contactEmail = process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim();
  const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();
  return (
    <main className="mx-auto w-full max-w-5xl px-5 py-12 sm:py-16">
      <div className="max-w-3xl"><p className="public-eyebrow">Contact</p><h1 className="mt-3 text-4xl font-bold tracking-[-0.04em] sm:text-5xl">Questions, corrections, and policy requests</h1><p className="mt-5 text-lg leading-8 text-[color:var(--muted)]">Use the official contact methods below for factual corrections, privacy questions, editorial concerns, or technical issues.</p></div>
      <div className="mt-8 grid gap-5 md:grid-cols-2">
        <section className="public-card p-6"><h2 className="text-xl font-semibold">Email</h2>{contactEmail ? <><p className="mt-3 text-[color:var(--muted)]">For privacy, corrections, legal, or editorial questions:</p><a className="public-button public-button-primary mt-5" href={`mailto:${contactEmail}`}>{contactEmail}</a></> : <p className="mt-3 leading-7 text-[color:var(--muted)]">A public contact email has not been configured yet. Set <code className="rounded-[2px] bg-[color:var(--surface)] px-1.5 py-0.5 text-sm">NEXT_PUBLIC_CONTACT_EMAIL</code> before production launch.</p>}</section>
        <section className="public-card p-6"><h2 className="text-xl font-semibold">Telegram</h2>{telegramChannelUrl ? <><p className="mt-3 text-[color:var(--muted)]">Follow the official channel for public LearnLoot updates.</p><a className="public-button public-button-secondary mt-5" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">Open Telegram ↗</a></> : <p className="mt-3 text-[color:var(--muted)]">The public Telegram channel is not configured in this environment.</p>}</section>
      </div>
      <div className="public-card-muted mt-6 p-5 text-sm leading-6 text-[color:var(--muted)]"><strong className="text-[color:var(--foreground)]">Privacy note:</strong> this page intentionally does not include a contact form, so LearnLoot does not need to collect message contents through the public website just to receive an inquiry.</div>
    </main>
  );
}
