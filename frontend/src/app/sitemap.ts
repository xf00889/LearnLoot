import type { MetadataRoute } from "next";
import { getCourseSitemapEntries, getShoppingSitemapEntries } from "@/lib/api";
import { getSiteUrl } from "@/lib/seo";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = getSiteUrl();
  const baseEntries: MetadataRoute.Sitemap = [
    { url: `${siteUrl}/`, changeFrequency: "daily", priority: 1 },
    { url: `${siteUrl}/courses`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${siteUrl}/shop`, changeFrequency: "daily", priority: 0.9 },
    { url: `${siteUrl}/shop/top-10`, changeFrequency: "daily", priority: 0.8 },
    { url: `${siteUrl}/shop/flash-deals`, changeFrequency: "hourly", priority: 0.8 },
    { url: `${siteUrl}/shop/guides`, changeFrequency: "weekly", priority: 0.8 },
  ];

  try {
    const [courses, shopping] = await Promise.all([
      getCourseSitemapEntries(),
      getShoppingSitemapEntries(),
    ]);
    return [
      ...baseEntries,
      ...courses.results.map((entry) => ({
        url: entry.url,
        lastModified: new Date(entry.last_modified),
        changeFrequency: "daily" as const,
        priority: 0.7,
      })),
      ...shopping.results.map((entry) => ({
        url: entry.url,
        lastModified: new Date(entry.last_modified),
        changeFrequency: "weekly" as const,
        priority: 0.7,
      })),
    ];
  } catch {
    return baseEntries;
  }
}
