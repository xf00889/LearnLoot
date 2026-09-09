import type { Metadata } from "next";
import { PolicyPage } from "@/components/policy-page";

export const metadata: Metadata = { title: "Editorial policy", description: "How LearnLoot approaches shopping guides, product rankings, disclosures, and editorial independence.", alternates: { canonical: "/editorial-policy" } };

export default function EditorialPolicyPage() {
  return <PolicyPage eyebrow="Trust policy" title="Editorial policy" intro="LearnLoot shopping content is manually managed editorial material. This page describes the standards the CMS and public experience are designed to support.">
    <h2>1. Original value</h2><p>Shopping posts should add original context rather than merely reproduce merchant descriptions. Useful editorial content can include comparisons, trade-offs, pros and cons, intended use cases, buying notes, and reasons for a ranking.</p>
    <h2>2. Separation from course discovery</h2><p>Shopping editorial and course discovery are separate systems. Commission-earning shopping destinations do not turn Udemy course links into monetized course referrals.</p>
    <h2>3. Rankings and recommendations</h2><p>Editors should rank and describe products based on the usefulness of the recommendation to the reader. Affiliate eligibility should not be presented as evidence that a product is better. If commercial arrangements ever materially affect placement, LearnLoot should disclose that relationship clearly.</p>
    <h2>4. Merchant information</h2><p>Prices, availability, seller information, and product details can change. LearnLoot may show editorially entered price information, but readers should verify the live merchant listing before purchasing.</p>
    <h2>5. Affiliate disclosure</h2><p>Shopping pages can include controlled outbound links to manually entered Shopee destinations. Relevant pages should display an affiliate disclosure and use sponsored/nofollow link semantics where appropriate.</p>
    <h2>6. Corrections</h2><p>Material factual errors should be corrected when identified. See the Corrections Policy for how LearnLoot handles correction requests.</p>
  </PolicyPage>;
}
