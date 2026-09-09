"use client";

import DeleteOutline from "@mui/icons-material/DeleteOutline";
import { Button, Card, CardContent, CardMedia, Grid, IconButton, Stack, TextField, Typography } from "@mui/material";
import { ChangeEvent, useEffect, useState } from "react";
import { deleteMedia, getMediaAssets, uploadMedia, type MediaAsset } from "@/lib/admin-api";

export default function AdminMediaPage() {
  const [assets, setAssets] = useState<MediaAsset[]>([]); const [title, setTitle] = useState(""); const [altText, setAltText] = useState(""); const [busy, setBusy] = useState(false);
  const refresh = () => getMediaAssets().then((data) => setAssets(data.results));
  useEffect(() => { refresh(); }, []);
  async function choose(event: ChangeEvent<HTMLInputElement>) { const file = event.target.files?.[0]; if (!file) return; setBusy(true); try { await uploadMedia(file, title, altText); setTitle(""); setAltText(""); await refresh(); } finally { setBusy(false); event.target.value = ""; } }
  return <Stack spacing={3}><div><Typography variant="h4" fontWeight={900}>Media Library</Typography><Typography color="text.secondary">Images uploaded here can also be inserted directly from CKEditor uploads.</Typography></div><Stack direction={{ xs: "column", md: "row" }} gap={1.5}><TextField size="small" label="Title" value={title} onChange={(e) => setTitle(e.target.value)} /><TextField size="small" label="Alt text" value={altText} onChange={(e) => setAltText(e.target.value)} /><Button component="label" variant="contained" disabled={busy}>{busy ? "Uploading..." : "Upload image"}<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={choose} /></Button></Stack><Grid container spacing={2}>{assets.map((asset) => <Grid key={asset.id} size={{ xs: 12, sm: 6, md: 4, lg: 3 }}><Card variant="outlined"><CardMedia component="img" height="150" image={asset.url} alt={asset.alt_text || asset.title || asset.name} sx={{ objectFit: "cover" }} /><CardContent sx={{ display: "flex", gap: 1, alignItems: "flex-start" }}><div style={{ flex: 1, minWidth: 0 }}><Typography fontWeight={800} noWrap>{asset.title || asset.name}</Typography><Typography variant="caption" color="text.secondary">{Math.round(asset.size_bytes / 1024)} KB · {new Date(asset.created_at).toLocaleDateString()}</Typography></div><IconButton size="small" aria-label="Delete media" onClick={async () => { await deleteMedia(asset.id); await refresh(); }}><DeleteOutline /></IconButton></CardContent></Card></Grid>)}</Grid></Stack>;
}
