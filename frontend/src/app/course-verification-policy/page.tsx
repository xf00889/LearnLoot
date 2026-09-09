import type { Metadata } from "next";
import { PolicyPage } from "@/components/policy-page";

export const metadata: Metadata = { title: "Course verification policy", description: "How LearnLoot discovers, checks, publishes, rechecks, and removes free-course opportunities.", alternates: { canonical: "/course-verification-policy" } };

export default function CourseVerificationPolicyPage() {
  return <PolicyPage eyebrow="Trust policy" title="Course verification policy" intro="This policy explains what LearnLoot means when it presents a course as currently free and how public course eligibility is determined.">
    <h2>1. Discovery sources</h2><p>LearnLoot uses provider-isolated discovery code to read permitted public course information. Udemy discovery is compliance-first: LearnLoot does not rely on private APIs, login-required endpoints, paid-course content access, authentication bypass, or scraping-evasion techniques.</p>
    <h2>2. What “Free” means</h2><p>A public LearnLoot course must have a latest price observation that indicates the course is free, with no positive amount recorded for that observation. “Free” describes the latest verified observation available to LearnLoot; it is not a promise that the provider will keep the course free indefinitely.</p>
    <h2>3. Publication requirements</h2><p>Public course pages require an active course, an active provider, a current publication-eligibility result, a recent check within LearnLoot&apos;s configured freshness window, and a safe canonical outbound destination. If any of those conditions stops being true, the course can disappear from public results.</p>
    <h2>4. Scores and quality signals</h2><p>LearnLoot may use rating, review, freshness, price, and other internal quality signals to evaluate publication eligibility. A LearnLoot score is an internal ranking signal, not a credential, accreditation, learning-outcome guarantee, or provider endorsement.</p>
    <h2>5. Human CMS fields</h2><p>Editors can manage public titles, descriptions, categories, language metadata, images, SEO fields, and other editorial overrides. Automated discovery is designed not to overwrite protected human-managed fields such as manually assigned LearnLoot categories.</p>
    <h2>6. Rechecking and changes</h2><p>Course availability, pricing, ratings, and provider pages can change after LearnLoot checks them. Visitors should confirm the current provider page before enrolling. A later discovery or price observation can cause a previously public course to become unavailable on LearnLoot.</p>
    <h2>7. Provider relationship</h2><p>LearnLoot is an independent discovery service and does not deliver third-party course content. Udemy course links are non-affiliate within LearnLoot&apos;s current course workflow.</p>
  </PolicyPage>;
}
