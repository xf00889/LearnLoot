"use client";

import { Alert, Button, MenuItem, Paper, Stack, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { createAdminShoppingPost, getAdminCategories, type AdminCategory } from "@/lib/admin-api";

export default function AdminShopNewPage() {
  const router = useRouter();
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [postType, setPostType] = useState("top_10");
  const [shortDescription, setShortDescription] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [language, setLanguage] = useState("");
  const [affiliateUrl, setAffiliateUrl] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getAdminCategories("affiliate")
      .then((data) => setCategories(data.results.filter((category) => category.is_active)))
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load categories."));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const post = await createAdminShoppingPost({
        title,
        slug,
        post_type: postType,
        short_description: shortDescription,
        category_id: categoryId ? Number(categoryId) : null,
        language,
        affiliate_url: affiliateUrl,
      });
      router.replace(`/admin/shop/${post.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create post.");
    }
  }

  return (
    <Stack spacing={2}>
      <div><Typography variant="h4" fontWeight={900}>New affiliate content</Typography><Typography color="text.secondary">Create the draft with its first affiliate link, then add rich content and more products.</Typography></div>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Paper component="form" onSubmit={submit} variant="outlined" sx={{ p: 3, maxWidth: 760 }}>
        <Stack spacing={2}>
          <TextField required label="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
          <TextField label="Slug (optional)" value={slug} onChange={(e) => setSlug(e.target.value)} helperText="Leave blank to generate from the title." />
          <TextField select label="Post type" value={postType} onChange={(e) => setPostType(e.target.value)}><MenuItem value="top_10">Top 10 / ranked list</MenuItem><MenuItem value="flash_deals">Flash deals</MenuItem><MenuItem value="buying_guide">Buying guide</MenuItem><MenuItem value="roundup">Product roundup</MenuItem><MenuItem value="article">Article</MenuItem></TextField>
          <TextField multiline minRows={2} label="Short description" inputProps={{ maxLength: 500 }} value={shortDescription} onChange={(e) => setShortDescription(e.target.value)} helperText={`${shortDescription.length}/500`} />
          <TextField select label="Category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}><MenuItem value=""><em>No category</em></MenuItem>{categories.map((category) => <MenuItem key={category.id} value={String(category.id)}>{category.name}</MenuItem>)}</TextField>
          <TextField label="Language (optional)" value={language} onChange={(e) => setLanguage(e.target.value)} placeholder="English" />
          <TextField required type="url" label="Shopee affiliate link" value={affiliateUrl} onChange={(e) => setAffiliateUrl(e.target.value)} placeholder="https://shopee.ph/..." helperText="Creates the first affiliate item using the content title." />
          <Button type="submit" variant="contained" sx={{ alignSelf: "flex-start" }}>Create draft and add link</Button>
        </Stack>
      </Paper>
    </Stack>
  );
}
