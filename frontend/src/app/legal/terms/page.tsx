import type { Metadata } from "next";
import { PolicyPage } from "@/components/policy-page";

export const metadata: Metadata = { title: "Terms of use", description: "Terms governing use of LearnLoot, course discovery pages, shopping editorial, and third-party outbound links.", alternates: { canonical: "/legal/terms" } };

export default function TermsPage() {
  return <PolicyPage eyebrow="Legal" title="Terms of use" intro="These terms describe the basic conditions for using LearnLoot and following third-party destinations surfaced by the service.">
    <h2>1. Nature of the service</h2><p>LearnLoot is an independent information, discovery, and editorial service. It does not provide the third-party courses it lists and does not act as the merchant for products linked from shopping editorial.</p>
    <h2>2. Course information</h2><p>LearnLoot attempts to show recently checked course opportunities that meet its publication rules. Course price, availability, content, instructor information, ratings, and provider terms can change after a LearnLoot check. Always verify the current provider page before enrolling.</p>
    <h2>3. Shopping information</h2><p>Shopping articles can include editorial descriptions, rankings, prices entered in the CMS, and outbound Shopee destinations. Merchant price, stock, shipping, seller status, product specifications, and promotion terms can change. Verify the live merchant listing before making a purchase.</p>
    <h2>4. External services</h2><p>When you follow an outbound course, shopping, or Telegram link, you leave LearnLoot. Your use of the destination is governed by that third party&apos;s own terms, privacy policy, eligibility rules, payment terms, and other requirements.</p>
    <h2>5. Affiliate relationships</h2><p>Certain shopping links may generate a commission for LearnLoot from qualifying purchases. Udemy course links in the current course workflow are non-affiliate. See the Affiliate Disclosure for more detail.</p>
    <h2>6. Acceptable use</h2><p>Do not misuse LearnLoot to interfere with service operation, attempt unauthorized access to staff systems, bypass security controls, submit malicious traffic, or use the service in a way that violates applicable law or third-party rights.</p>
    <h2>7. Intellectual property and trademarks</h2><p>LearnLoot&apos;s original site design, editorial copy, and platform materials remain subject to applicable intellectual-property rights. Third-party names, course materials, merchant content, logos, and trademarks belong to their respective owners. Reference to a third party does not by itself imply sponsorship or endorsement.</p>
    <h2>8. No guarantee</h2><p>LearnLoot provides informational content on an as-available basis. The service cannot guarantee uninterrupted availability, permanent free access to a course, a particular learning outcome, merchant inventory, pricing accuracy after a check, or suitability of a product for every user.</p>
    <h2>9. Changes</h2><p>LearnLoot may update site features and these terms as the service evolves. Material policy changes should be reflected by updating the date shown on this page.</p>
  </PolicyPage>;
}
