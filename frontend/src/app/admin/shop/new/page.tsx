"use client";

import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { createAdminShoppingPost } from "@/lib/admin-api";

export default function AdminShopNewPage() {
  const router = useRouter();
  const [title, setTitle] = useState(""); const [slug, setSlug] = useState(""); const [postType, setPostType] = useState("top_10"); const [error, setError] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); setError(""); try { const post = await createAdminShoppingPost({ title, slug, post_type: postType }); router.replace(`/admin/shop/${post.id}`); } catch (e) { setError(e instanceof Error ? e.message : "Unable to create post."); } }
  return <Stack spacing={2}><div><Typography variant="h4" fontWeight={900}>New shopping post</Typography><Typography color="text.secondary">Create the draft first, then add rich content and Shopee products.</Typography></div>{error ? <Alert severity="error">{error}</Alert> : null}<Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 3, maxWidth: 760 }}><Stack spacing={2}><TextField required label="Title" value={title} onChange={(e) => setTitle(e.target.value)} /><TextField label="Slug (optional)" value={slug} onChange={(e) => setSlug(e.target.value)} helperText="Leave blank to generate from the title." /><TextField select label="Post type" value={postType} onChange={(e) => setPostType(e.target.value)}><MenuItem value="top_10">Top 10 / ranked list</MenuItem><MenuItem value="flash_deals">Flash deals</MenuItem><MenuItem value="buying_guide">Buying guide</MenuItem><MenuItem value="roundup">Product roundup</MenuItem><MenuItem value="article">Article</MenuItem></TextField><Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>Create draft</Button></Stack></Paper></Stack>;
}
