import type { Metadata } from "next";
import Link from "next/link";
import { PolicyPage } from "@/components/policy-page";

export const metadata: Metadata = { title: "Corrections policy", description: "How to request a factual correction to LearnLoot course metadata, shopping editorial, or public policy information.", alternates: { canonical: "/corrections-policy" } };

export default function CorrectionsPolicyPage() {
  return <PolicyPage eyebrow="Trust policy" title="Corrections policy" intro="LearnLoot aims to correct meaningful factual errors without hiding the fact that third-party course and merchant information can change quickly.">
    <h2>1. What can be reported</h2><ul><li>A course that is no longer free or no longer available.</li><li>Incorrect instructor, category, language, image, or descriptive metadata.</li><li>A shopping guide statement that is materially inaccurate.</li><li>An expired, incorrect, or unsafe outbound destination.</li><li>An error in a LearnLoot policy or disclosure page.</li></ul>
    <h2>2. How to request a correction</h2><p>Use the <Link href="/contact">Contact page</Link>. Include the LearnLoot URL, the statement or field you believe is wrong, and a reliable source or current provider/merchant page when available.</p>
    <h2>3. Review approach</h2><p>LearnLoot may compare the report with current public provider or merchant information, internal discovery observations, and manually managed CMS fields. Automated source data and human editorial overrides are kept separate so an automated refresh does not silently erase protected editorial decisions.</p>
    <h2>4. Time-sensitive information</h2><p>Course price and merchant availability can change after publication. A changed external condition is not always an editorial error, but LearnLoot may update or remove the affected public record once the new condition is verified.</p>
  </PolicyPage>;
}
