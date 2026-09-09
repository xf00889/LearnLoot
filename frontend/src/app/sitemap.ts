import type { MetadataRoute } from "next";
import { getCourseSitemapEntries, getShoppingSitemapEntries } from "@/lib/api";
import { getSiteUrl } from "@/lib/seo";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const siteUrl = getSiteUrl();
  const baseEntries: MetadataRoute.Sitemap = [
    { url: `${siteUrl}/`, changeFrequency: "daily", priority: 1 },
    { url: `${siteUrl}/courses`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${siteUrl}/courses/categories`, changeFrequency: "daily", priority: 0.75 },
    { url: `${siteUrl}/shop`, changeFrequency: "daily", priority: 0.9 },
    { url: `${siteUrl}/shop/top-10`, changeFrequency: "daily", priority: 0.8 },
    { url: `${siteUrl}/shop/flash-deals`, changeFrequency: "hourly", priority: 0.8 },
    { url: `${siteUrl}/shop/guides`, changeFrequency: "weekly", priority: 0.8 },
    { url: `${siteUrl}/about`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${siteUrl}/how-it-works`, changeFrequency: "monthly", priority: 0.6 },
    { url: `${siteUrl}/contact`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/course-verification-policy`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${siteUrl}/editorial-policy`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${siteUrl}/corrections-policy`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/legal`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/legal/privacy`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/legal/terms`, changeFrequency: "monthly", priority: 0.4 },
    { url: `${siteUrl}/legal/affiliate-disclosure`, changeFrequency: "monthly", priority: 0.4 },
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
