"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

const primaryLinks = [
  { href: "/courses", label: "Courses" },
  { href: "/courses/categories", label: "Categories" },
  { href: "/shop", label: "Shop & Deals" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/courses") return pathname === href || pathname.startsWith("/courses/") && pathname !== "/courses/categories";
  if (href === "/shop") return pathname === href || pathname.startsWith("/shop/");
  return pathname === href;
}

export function SiteChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname.startsWith("/admin")) return <>{children}</>;

  const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();
  const contactEmail = process.env.NEXT_PUBLIC_CONTACT_EMAIL?.trim();

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-[color:var(--border)] bg-[color:var(--surface-strong)]/95 backdrop-blur-sm">
        <nav className="mx-auto flex min-h-16 w-full max-w-7xl items-center justify-between gap-5 px-5" aria-label="Primary navigation">
          <Link className="flex items-center gap-2 text-lg font-bold tracking-[-0.03em]" href="/">
            <span className="flex h-8 w-8 items-center justify-center rounded-[4px] bg-[color:var(--accent)] text-sm font-bold text-white">LL</span>
            <span>LearnLoot</span>
          </Link>

          <div className="hidden items-center gap-1 md:flex">
            {primaryLinks.map((link) => (
              <Link
                className={`border-b-2 px-3 py-5 text-sm font-semibold transition-colors ${
                  isActive(pathname, link.href)
                    ? "border-[color:var(--accent)] text-[color:var(--foreground)]"
                    : "border-transparent text-[color:var(--muted)] hover:text-[color:var(--foreground)]"
                }`}
                href={link.href}
                key={link.href}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden items-center gap-2 lg:flex">
            <Link className="public-button public-button-secondary text-sm" href="/courses">Search courses</Link>
            {telegramChannelUrl ? (
              <a className="public-button public-button-primary text-sm" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">
                Telegram <span aria-hidden="true">↗</span>
              </a>
            ) : null}
          </div>

          <details className="relative md:hidden">
            <summary className="public-button public-button-secondary cursor-pointer list-none text-sm">Menu</summary>
            <div className="absolute right-0 mt-2 w-64 rounded-[6px] border border-[color:var(--border)] bg-[color:var(--surface-strong)] p-2 shadow-lg">
              {primaryLinks.map((link) => (
                <Link className="block rounded-[4px] px-3 py-2.5 text-sm font-semibold hover:bg-[color:var(--surface)]" href={link.href} key={link.href}>
                  {link.label}
                </Link>
              ))}
              {telegramChannelUrl ? (
                <a className="mt-1 block rounded-[4px] px-3 py-2.5 text-sm font-semibold text-[color:var(--accent)] hover:bg-[color:var(--surface)]" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">
                  Telegram ↗
                </a>
              ) : null}
            </div>
          </details>
        </nav>
      </header>

      {children}

      <footer className="mt-auto border-t border-[color:var(--border)] bg-[color:var(--surface-strong)]">
        <div className="mx-auto grid w-full max-w-7xl gap-10 px-5 py-12 sm:grid-cols-2 lg:grid-cols-[1.35fr_1fr_1fr_1fr]">
          <div>
            <Link className="text-lg font-bold tracking-[-0.03em]" href="/">LearnLoot</Link>
            <p className="mt-3 max-w-sm text-sm leading-6 text-[color:var(--muted)]">
              Recently checked free-course opportunities and independently edited shopping guides, kept intentionally separate.
            </p>
            {telegramChannelUrl ? (
              <a className="public-link mt-4 inline-flex text-sm" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">Follow the Telegram channel ↗</a>
            ) : null}
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[color:var(--muted)]">Explore</p>
            <div className="mt-4 grid gap-2.5 text-sm">
              <Link href="/courses">Free courses</Link>
              <Link href="/courses/categories">Course categories</Link>
              <Link href="/shop">Shop & deals</Link>
              <Link href="/shop/guides">Buying guides</Link>
              <Link href="/shop/top-10">Top 10 lists</Link>
              <Link href="/shop/flash-deals">Flash deals</Link>
            </div>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[color:var(--muted)]">Trust</p>
            <div className="mt-4 grid gap-2.5 text-sm">
              <Link href="/about">About</Link>
              <Link href="/how-it-works">How it works</Link>
              <Link href="/course-verification-policy">Course verification policy</Link>
              <Link href="/editorial-policy">Editorial policy</Link>
              <Link href="/corrections-policy">Corrections policy</Link>
              <Link href="/contact">Contact</Link>
            </div>
          </div>

          <div>
            <p className="text-xs font-bold uppercase tracking-[0.14em] text-[color:var(--muted)]">Legal</p>
            <div className="mt-4 grid gap-2.5 text-sm">
              <Link href="/legal">Legal center</Link>
              <Link href="/legal/privacy">Privacy policy</Link>
              <Link href="/legal/terms">Terms of use</Link>
              <Link href="/legal/affiliate-disclosure">Affiliate disclosure</Link>
              {contactEmail ? <a href={`mailto:${contactEmail}`}>{contactEmail}</a> : null}
            </div>
          </div>
        </div>

        <div className="border-t border-[color:var(--border)]">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-3 px-5 py-6 text-xs leading-5 text-[color:var(--muted)] md:flex-row md:items-start md:justify-between">
            <p>© 2026 LearnLoot. All rights reserved.</p>
            <p className="max-w-3xl md:text-right">
              Course availability and merchant prices can change. Confirm current details with the provider or merchant. LearnLoot is an independent service; Udemy course links are non-affiliate, while certain shopping links may generate a commission.
            </p>
          </div>
        </div>
      </footer>
    </>
  );
}
