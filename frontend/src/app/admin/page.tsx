"use client";

import { Card, CardContent, Grid, Stack, Typography, Alert } from "@mui/material";
import { useEffect, useState } from "react";
import { getDashboard, type DashboardPayload } from "@/lib/admin-api";

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { getDashboard().then(setData).catch((e) => setError(e instanceof Error ? e.message : "Unable to load dashboard.")); }, []);
  const cards = data ? [
    ["Courses", data.courses.total, `${data.courses.active} active / ${data.courses.customized} customized`],
    ["Shopping posts", data.shopping.posts, `${data.shopping.published} published / ${data.shopping.products} products`],
    ["Course clicks", data.analytics.course_clicks, "Tracked outbound course visits"],
    ["Shopping clicks", data.analytics.shopping_clicks, "Tracked Shopee affiliate visits"],
    ["Media assets", data.media.assets, "CMS image library"],
    ["Telegram queue", data.publishing.queued, `${data.publishing.telegram_failed} failed deliveries`],
  ] : [];
  return <Stack spacing={3}>
    <div><Typography variant="h4" fontWeight={900}>Dashboard</Typography><Typography color="text.secondary">Content, publishing, analytics, and discovery at a glance.</Typography></div>
    {error ? <Alert severity="error">{error}</Alert> : null}
    <Grid container spacing={2}>{cards.map(([label, value, detail]) => <Grid size={{ xs: 12, sm: 6, lg: 4 }} key={String(label)}><Card variant="outlined"><CardContent><Typography color="text.secondary" variant="body2">{label}</Typography><Typography variant="h4" fontWeight={900} sx={{ my: 0.5 }}>{value}</Typography><Typography color="text.secondary" variant="caption">{detail}</Typography></CardContent></Card></Grid>)}</Grid>
    {data ? <Card variant="outlined"><CardContent><Typography fontWeight={800}>Latest discovery</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>{data.discovery.latest_status ?? "No discovery run yet"}{data.discovery.latest_started_at ? ` · ${new Date(data.discovery.latest_started_at).toLocaleString()}` : ""}</Typography></CardContent></Card> : null}
  </Stack>;
}
