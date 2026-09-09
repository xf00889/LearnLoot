"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function SiteChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname.startsWith("/admin")) return <>{children}</>;

  const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();
  return (
    <>
      <header className="border-b border-[color:var(--border)] bg-[color:var(--surface)]/80 backdrop-blur">
        <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4">
          <Link className="text-lg font-black tracking-tight" href="/">LearnLoot</Link>
          <div className="flex items-center gap-4 text-sm font-semibold text-[color:var(--muted)]">
            <Link className="hover:text-[color:var(--foreground)]" href="/courses">Courses</Link>
            <Link className="hover:text-[color:var(--foreground)]" href="/shop">Shop & Deals</Link>
            {telegramChannelUrl ? <a className="hover:text-[color:var(--foreground)]" href={telegramChannelUrl} rel="noopener noreferrer" target="_blank">Telegram Channel</a> : null}
          </div>
        </nav>
      </header>
      {children}
      <footer className="mt-auto border-t border-[color:var(--border)] px-5 py-8 text-center text-sm text-[color:var(--muted)]">
        <p>LearnLoot verifies free-course opportunities and publishes independently written shopping guides.</p>
        <p className="mt-2">Some shopping links are affiliate links; LearnLoot may earn a commission from qualifying purchases at no additional cost to you.</p>
      </footer>
    </>
  );
}
