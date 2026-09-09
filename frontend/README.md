# LearnLoot Frontend

Next.js public website for LearnLoot course discovery, manually curated shopping
content, Telegram traffic, and SEO landing pages.

## Development

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Default local settings:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_TELEGRAM_CHANNEL_URL=
GOOGLE_SITE_VERIFICATION=
```

`GOOGLE_SITE_VERIFICATION` is optional and renders the Google site-verification
meta tag through the Next.js Metadata API when configured.

## Public routes

- `/` - homepage for courses and editorial shopping content.
- `/courses` - searchable public free-course catalog.
- `/courses/[provider]/[slug]` - SEO course landing page.
- `/shop` - shopping editorial hub.
- `/shop/top-10` - ranked product-list archive.
- `/shop/flash-deals` - flash-deal archive.
- `/shop/guides` - buying-guide archive.
- `/shop/[slug]` - manually authored shopping article/product roundup.
- `/robots.txt` - generated crawler rules.
- `/sitemap.xml` - generated site sitemap with public courses and shopping posts.

## Course CMS behavior

Udemy discovery still owns the scraped source fields. Django Admin exposes
operator-controlled editorial title, description, image, slug, SEO title, meta
description, meta keywords, and social image. These CMS overrides are not
replaced by a later scraper refresh; blank overrides fall back to current scraped
metadata.

Course CTAs continue to use the non-affiliate `/go/<provider>/<course>/` route and
then the validated canonical provider URL.

## Shopping affiliate content

Shopping content is a separate CMS domain. The operator manually creates the
article, slug, cover image, SEO fields, product ranking, product image, notes,
prices, and Shopee affiliate destination in Django Admin. The public API never
exposes the raw affiliate destination; page CTAs use `/go/shop/...` and are
marked `rel="sponsored nofollow"`.

Published shopping pages include an affiliate disclosure and structured data for
Article, ItemList, and BreadcrumbList. Product descriptions and comparisons
should remain original editorial content rather than copied merchant text.


## Custom admin CMS (Phase 11)

`/admin` is the LearnLoot custom Material UI CMS. It uses Django session authentication with `credentials: include`, CSRF protection, CKEditor 5 for rich text, and the staff-only `/api/admin/` endpoints. The admin is marked `noindex`. The editor is client-only (`next/dynamic` with `ssr: false`) because CKEditor relies on browser APIs.

The example `NEXT_PUBLIC_CKEDITOR_LICENSE_KEY=GPL` declares GPL self-hosting. Replace it with an appropriate commercial key if the project cannot comply with GPL requirements.
