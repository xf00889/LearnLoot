import type { Metadata } from "next";
import { PolicyPage } from "@/components/policy-page";

export const metadata: Metadata = { title: "Affiliate disclosure", description: "How LearnLoot uses qualifying shopping affiliate links while keeping Udemy course links non-affiliate.", alternates: { canonical: "/legal/affiliate-disclosure" } };

export default function AffiliateDisclosurePage() {
  return <PolicyPage eyebrow="Legal" title="Affiliate disclosure" intro="LearnLoot separates course-provider links from shopping monetization so visitors can tell when a commercial relationship may exist.">
    <h2>1. Shopping links</h2><p>Certain product links in LearnLoot shopping articles may be affiliate destinations. If a visitor follows one of those links and completes a qualifying purchase, LearnLoot may receive a commission from the merchant or affiliate program.</p>
    <h2>2. Price to the visitor</h2><p>An affiliate relationship does not by itself mean LearnLoot adds a separate fee to the visitor&apos;s purchase. The final price, fees, discounts, eligibility rules, and checkout terms are determined by the merchant and should be verified on the destination page.</p>
    <h2>3. Course links</h2><p>Udemy course links in LearnLoot&apos;s current course workflow are non-affiliate. Course discovery and shopping affiliate content are intentionally separate systems.</p>
    <h2>4. Disclosure placement</h2><p>Shopping articles can display an affiliate disclosure near the article content, and qualifying outbound shopping links use sponsored/nofollow relationship attributes where appropriate. LearnLoot also repeats the general disclosure in the public footer.</p>
    <h2>5. Editorial independence</h2><p>A commission relationship should not be presented as proof that a product is superior. LearnLoot&apos;s Editorial Policy describes the intended standards for rankings, comparisons, and buying recommendations.</p>
  </PolicyPage>;
}
