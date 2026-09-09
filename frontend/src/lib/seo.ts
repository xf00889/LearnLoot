export const SITE_NAME = "LearnLoot";
export const SITE_DESCRIPTION =
  "Discover verified free courses and independently curated shopping guides, ranked lists, and flash deals.";

export function getSiteUrl(): string {
  return (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");
}

export function canonicalUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${getSiteUrl()}${normalizedPath}`;
}

export function csvKeywords(value: string | undefined): string[] | undefined {
  const keywords = (value ?? "")
    .split(",")
    .map((keyword) => keyword.trim())
    .filter(Boolean);
  return keywords.length ? keywords : undefined;
}

export function splitEditorialLines(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}
