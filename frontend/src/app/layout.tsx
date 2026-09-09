import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { JsonLd } from "@/components/json-ld";
import { SITE_DESCRIPTION, SITE_NAME, getSiteUrl } from "@/lib/seo";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

const siteUrl = getSiteUrl();
const telegramChannelUrl = process.env.NEXT_PUBLIC_TELEGRAM_CHANNEL_URL?.trim();
const googleVerification = process.env.GOOGLE_SITE_VERIFICATION?.trim();

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  applicationName: SITE_NAME,
  title: {
    default: "LearnLoot - Free courses and curated deals",
    template: "%s | LearnLoot",
  },
  description: SITE_DESCRIPTION,
  authors: [{ name: SITE_NAME, url: siteUrl }],
  creator: SITE_NAME,
  publisher: SITE_NAME,
  keywords: [
    "free online courses",
    "Udemy free courses",
    "course deals",
    "Shopee deals",
    "shopping guides Philippines",
    "top products Philippines",
    "flash deals Philippines",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    url: siteUrl,
    siteName: SITE_NAME,
    title: "LearnLoot - Free courses and curated deals",
    description: SITE_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: "LearnLoot - Free courses and curated deals",
    description: SITE_DESCRIPTION,
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  verification: googleVerification ? { google: googleVerification } : undefined,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const websiteJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: SITE_NAME,
    url: siteUrl,
    description: SITE_DESCRIPTION,
  };
  const organizationJsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: SITE_NAME,
    url: siteUrl,
  };

  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <JsonLd data={[websiteJsonLd, organizationJsonLd]} />
        <header className="border-b border-[color:var(--border)] bg-[color:var(--surface)]/80 backdrop-blur">
          <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-4">
            <Link className="text-lg font-black tracking-tight" href="/">
              LearnLoot
            </Link>
            <div className="flex items-center gap-4 text-sm font-semibold text-[color:var(--muted)]">
              <Link className="hover:text-[color:var(--foreground)]" href="/courses">
                Courses
              </Link>
              <Link className="hover:text-[color:var(--foreground)]" href="/shop">
                Shop & Deals
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
          <p>
            LearnLoot verifies free-course opportunities and publishes independently
            written shopping guides.
          </p>
          <p className="mt-2">
            Some shopping links are affiliate links; LearnLoot may earn a commission
            from qualifying purchases at no additional cost to you.
          </p>
        </footer>
      </body>
    </html>
  );
}
