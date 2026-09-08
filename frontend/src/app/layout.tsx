import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "LearnLoot — Free course deals",
    template: "%s | LearnLoot",
  },
  description:
    "Fresh free-course deals checked by LearnLoot and shared through the Telegram channel.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="border-b border-[color:var(--border)] bg-[color:var(--surface)]/80 backdrop-blur">
          <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4">
            <Link className="text-lg font-black tracking-tight" href="/">
              LearnLoot
            </Link>
            <div className="flex items-center gap-4 text-sm font-semibold text-[color:var(--muted)]">
              <Link className="hover:text-[color:var(--foreground)]" href="/courses">
                Courses
              </Link>
              {telegramChannelUrl ? (
                <a
                  className="hover:text-[color:var(--foreground)]"
                  href={telegramChannelUrl}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Telegram Channel
                </a>
              ) : null}
            </div>
          </nav>
        </header>
        {children}
        <footer className="mt-auto border-t border-[color:var(--border)] px-5 py-8 text-center text-sm text-[color:var(--muted)]">
          LearnLoot verifies free-course opportunities before directing visitors to
          the course provider.
        </footer>
      </body>
    </html>
  );
}
