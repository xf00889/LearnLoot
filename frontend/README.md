# LearnLoot Frontend

Next.js public website for LearnLoot course-deal discovery and Telegram traffic.

## Development

Copy the frontend environment template and start the development server:

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

The default local settings are:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
NEXT_PUBLIC_SITE_URL=http://localhost:3000
NEXT_PUBLIC_TELEGRAM_CHANNEL_URL=
```

Set `NEXT_PUBLIC_TELEGRAM_CHANNEL_URL` to the public `https://t.me/...` channel
URL when you are ready to show follower CTAs.

## Public routes

- `/` — homepage with latest qualified free courses
- `/courses` — searchable public catalog
- `/courses/[provider]/[slug]` — SEO landing page used by Telegram channel posts

Telegram channel posts should point to the LearnLoot course landing page rather
than directly to the provider URL.

## Phase 9 outbound links

Course detail CTAs use the backend-provided `outbound_url` instead of exposing
the provider URL directly. Query attribution such as `source=telegram` and
`campaign=channel` is preserved on the tracked redirect. When the backend reports
an active approved affiliate destination, the CTA shows an affiliate disclosure
and uses the `sponsored` link relationship.
