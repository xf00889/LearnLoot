"use client";

import { Alert, Box, Button, Chip, Divider, Grid, MenuItem, Paper, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ClientRichTextEditor from "@/components/admin/client-rich-text-editor";
import {
  createAdminShoppingProduct,
  deleteAdminShoppingProduct,
  getAdminCategories,
  getAdminShoppingPost,
  updateAdminShoppingPost,
  updateAdminShoppingProduct,
  uploadShoppingPostCover,
  uploadShoppingProductImage,
  type AdminCategory,
  type AdminShoppingPostDetail,
  type AdminShoppingProduct,
} from "@/lib/admin-api";

type ProductDraft = {
  position: number;
  name: string;
  slug: string;
  affiliate_url: string;
  short_description: string;
  content: string;
  category_id: number | null;
  language: string;
  displayed_price: string;
  original_price: string;
  currency: string;
  badge: string;
  pros: string;
  cons: string;
  is_active: boolean;
};

const emptyProduct: ProductDraft = {
  position: 1,
  name: "",
  slug: "",
  affiliate_url: "",
  short_description: "",
  content: "",
  category_id: null,
  language: "",
  displayed_price: "",
  original_price: "",
  currency: "PHP",
  badge: "",
  pros: "",
  cons: "",
  is_active: true,
};

export default function AdminShopEditPage() {
  const params = useParams<{ id: string }>();
  const [post, setPost] = useState<AdminShoppingPostDetail | null>(null);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [tab, setTab] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [draftProduct, setDraftProduct] = useState<ProductDraft>({ ...emptyProduct });

  useEffect(() => {
    Promise.all([getAdminShoppingPost(params.id), getAdminCategories("affiliate")])
      .then(([value, categoryData]) => {
        setPost(value);
        setCategories(categoryData.results.filter((category) => category.is_active || category.id === value.category?.id || value.products.some((product) => product.category?.id === category.id)));
        setDraftProduct({ ...emptyProduct, position: value.products.length + 1 });
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load post."));
  }, [params.id]);

  if (!post) return <Stack spacing={2}><Typography variant="h4" fontWeight={900}>Affiliate editor</Typography>{error ? <Alert severity="error">{error}</Alert> : <Typography>Loading...</Typography>}</Stack>;

  async function save() {
    const currentPost = post;
    if (!currentPost) return;
    setError(""); setMessage("");
    try {
      const updated = await updateAdminShoppingPost(currentPost.id, {
        title: currentPost.title,
        slug: currentPost.slug,
        post_type: currentPost.post_type,
        status: currentPost.status,
        short_description: currentPost.short_description,
        content: currentPost.content,
        category_id: currentPost.category?.id ?? null,
        language: currentPost.language ?? "",
        seo_title: currentPost.seo_title,
        meta_description: currentPost.meta_description,
        meta_keywords: currentPost.meta_keywords,
        is_featured: currentPost.is_featured,
      });
      setPost(updated);
      setMessage("Affiliate content saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
    }
  }

  async function addProduct() {
    const currentPost = post;
    if (!currentPost) return;
    setError("");
    try {
      await createAdminShoppingProduct(currentPost.id, draftProduct);
      const updated = await getAdminShoppingPost(currentPost.id);
      setPost(updated);
      setDraftProduct({ ...emptyProduct, position: updated.products.length + 1 });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to add product.");
    }
  }

  async function saveProduct(product: AdminShoppingProduct) {
    const currentPost = post;
    if (!currentPost) return;
    setError("");
    try {
      await updateAdminShoppingProduct(product.id, {
        position: product.position,
        name: product.name,
        slug: product.slug,
        short_description: product.short_description,
        content: product.content,
        category_id: product.category?.id ?? null,
        language: product.language ?? "",
        affiliate_url: product.affiliate_url,
        displayed_price: product.displayed_price,
        original_price: product.original_price,
        currency: product.currency,
        badge: product.badge,
        pros: product.pros,
        cons: product.cons,
        is_active: product.is_active,
      });
      setPost(await getAdminShoppingPost(currentPost.id));
      setMessage("Product saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save product.");
    }
  }

  async function removeProduct(id: number) {
    const currentPost = post;
    if (!currentPost) return;
    await deleteAdminShoppingProduct(id);
    setPost(await getAdminShoppingPost(currentPost.id));
  }

  function replaceProduct(index: number, next: AdminShoppingProduct) {
    const currentPost = post;
    if (!currentPost) return;
    const products = [...currentPost.products];
    products[index] = next;
    setPost({ ...currentPost, products });
  }

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <div><Typography variant="h4" fontWeight={900}>{post.title}</Typography><Typography color="text.secondary">Shopee affiliate editorial CMS</Typography></div>
        <Button variant="contained" onClick={save}>Save changes</Button>
      </Stack>
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper variant="outlined">
        <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable"><Tab label="Content" /><Tab label="Products" /><Tab label="SEO" /></Tabs>
        <Divider />
        <Box sx={{ p: 3 }}>
          {tab === 0 ? (
            <Stack spacing={2.5}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="Title" value={post.title} onChange={(e) => setPost({ ...post, title: e.target.value })} /></Grid>
                <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Status" value={post.status} onChange={(e) => setPost({ ...post, status: e.target.value })}><MenuItem value="draft">Draft</MenuItem><MenuItem value="published">Published</MenuItem><MenuItem value="archived">Archived</MenuItem></TextField></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Slug" value={post.slug} onChange={(e) => setPost({ ...post, slug: e.target.value })} /></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField select fullWidth label="Post type" value={post.post_type} onChange={(e) => setPost({ ...post, post_type: e.target.value })}><MenuItem value="top_10">Top 10</MenuItem><MenuItem value="flash_deals">Flash deals</MenuItem><MenuItem value="buying_guide">Buying guide</MenuItem><MenuItem value="roundup">Roundup</MenuItem><MenuItem value="article">Article</MenuItem></TextField></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField select fullWidth label="Category" value={post.category?.id ?? ""} onChange={(e) => { const id = Number(e.target.value); setPost({ ...post, category: categories.find((category) => category.id === id) ?? null }); }}><MenuItem value=""><em>No category</em></MenuItem>{categories.map((category) => <MenuItem key={category.id} value={category.id}>{category.name}</MenuItem>)}</TextField></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Language (optional)" value={post.language ?? ""} onChange={(e) => setPost({ ...post, language: e.target.value || null })} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth multiline minRows={2} label="Short description" inputProps={{ maxLength: 500 }} value={post.short_description} onChange={(e) => setPost({ ...post, short_description: e.target.value, excerpt: e.target.value })} helperText={`${post.short_description.length}/500`} /></Grid>
              </Grid>
              <div><Typography fontWeight={800} sx={{ mb: 1 }}>Content</Typography><ClientRichTextEditor value={post.content} onChange={(content) => setPost({ ...post, content, body: content })} minHeight={420} /></div>
              <Stack direction="row" gap={1} alignItems="center"><Button component="label" variant="outlined">Upload cover image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; const result = await uploadShoppingPostCover(post.id, file); setPost({ ...post, cover_image_url: result.url }); e.target.value = ""; }} /></Button>{post.cover_image_url ? <Typography variant="caption" color="text.secondary">Cover image configured</Typography> : null}</Stack>
            </Stack>
          ) : null}

          {tab === 1 ? (
            <Stack spacing={2}>
              {post.products.map((product, index) => (
                <Paper variant="outlined" sx={{ p: 2 }} key={product.id}>
                  <Stack spacing={1.5}>
                    <Stack direction="row" justifyContent="space-between"><Typography fontWeight={800}>#{product.position} {product.name || "Product"}</Typography><Chip size="small" label={product.is_active ? "Active" : "Inactive"} /></Stack>
                    <Grid container spacing={1.5}>
                      <Grid size={{ xs: 12, md: 2 }}><TextField fullWidth type="number" label="Position" value={product.position} onChange={(e) => replaceProduct(index, { ...product, position: Number(e.target.value) })} /></Grid>
                      <Grid size={{ xs: 12, md: 5 }}><TextField fullWidth label="Product name" value={product.name} onChange={(e) => replaceProduct(index, { ...product, name: e.target.value })} /></Grid>
                      <Grid size={{ xs: 12, md: 5 }}><TextField fullWidth label="Slug" value={product.slug} onChange={(e) => replaceProduct(index, { ...product, slug: e.target.value })} /></Grid>
                      <Grid size={{ xs: 12, md: 6 }}><TextField select fullWidth label="Category" value={product.category?.id ?? ""} onChange={(e) => { const id = Number(e.target.value); replaceProduct(index, { ...product, category: categories.find((category) => category.id === id) ?? null }); }}><MenuItem value=""><em>No category</em></MenuItem>{categories.map((category) => <MenuItem key={category.id} value={category.id}>{category.name}</MenuItem>)}</TextField></Grid>
                      <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Language (optional)" value={product.language ?? ""} onChange={(e) => replaceProduct(index, { ...product, language: e.target.value || null })} /></Grid>
                    </Grid>
                    <TextField fullWidth label="Shopee affiliate URL" value={product.affiliate_url} onChange={(e) => replaceProduct(index, { ...product, affiliate_url: e.target.value })} />
                    <TextField fullWidth multiline minRows={2} label="Short description" value={product.short_description} onChange={(e) => replaceProduct(index, { ...product, short_description: e.target.value })} />
                    <div><Typography fontWeight={800} sx={{ mb: 1 }}>Content</Typography><ClientRichTextEditor value={product.content} onChange={(content) => replaceProduct(index, { ...product, content })} minHeight={220} /></div>
                    <Grid container spacing={1.5}><Grid size={{ xs: 12, md: 3 }}><TextField fullWidth label="Current price" value={product.displayed_price} onChange={(e) => replaceProduct(index, { ...product, displayed_price: e.target.value })} /></Grid><Grid size={{ xs: 12, md: 3 }}><TextField fullWidth label="Original price" value={product.original_price} onChange={(e) => replaceProduct(index, { ...product, original_price: e.target.value })} /></Grid><Grid size={{ xs: 12, md: 2 }}><TextField fullWidth label="Currency" value={product.currency} onChange={(e) => replaceProduct(index, { ...product, currency: e.target.value })} /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField fullWidth label="Badge" value={product.badge} onChange={(e) => replaceProduct(index, { ...product, badge: e.target.value })} /></Grid></Grid>
                    <Grid container spacing={1.5}><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth multiline minRows={2} label="Pros (one per line)" value={product.pros} onChange={(e) => replaceProduct(index, { ...product, pros: e.target.value })} /></Grid><Grid size={{ xs: 12, md: 6 }}><TextField fullWidth multiline minRows={2} label="Cons (one per line)" value={product.cons} onChange={(e) => replaceProduct(index, { ...product, cons: e.target.value })} /></Grid></Grid>
                    <Stack direction="row" gap={1} flexWrap="wrap"><Button size="small" variant="outlined" onClick={() => saveProduct(post.products[index])}>Save product</Button><Button size="small" component="label" variant="outlined">Upload image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; await uploadShoppingProductImage(product.id, file); setPost(await getAdminShoppingPost(post.id)); e.target.value = ""; }} /></Button><Button size="small" color="error" onClick={() => removeProduct(product.id)}>Delete</Button></Stack>
                  </Stack>
                </Paper>
              ))}

              <Divider />
              <Typography variant="h6" fontWeight={900}>Add product</Typography>
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 12, md: 2 }}><TextField fullWidth type="number" label="Position" value={draftProduct.position} onChange={(e) => setDraftProduct({ ...draftProduct, position: Number(e.target.value) })} /></Grid>
                <Grid size={{ xs: 12, md: 5 }}><TextField fullWidth label="Name" value={draftProduct.name} onChange={(e) => setDraftProduct({ ...draftProduct, name: e.target.value })} /></Grid>
                <Grid size={{ xs: 12, md: 5 }}><TextField fullWidth label="Slug" value={draftProduct.slug} onChange={(e) => setDraftProduct({ ...draftProduct, slug: e.target.value })} /></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField select fullWidth label="Category" value={draftProduct.category_id ?? ""} onChange={(e) => setDraftProduct({ ...draftProduct, category_id: e.target.value ? Number(e.target.value) : null })}><MenuItem value=""><em>No category</em></MenuItem>{categories.map((category) => <MenuItem key={category.id} value={category.id}>{category.name}</MenuItem>)}</TextField></Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Language (optional)" value={draftProduct.language} onChange={(e) => setDraftProduct({ ...draftProduct, language: e.target.value })} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth label="Shopee affiliate URL" value={draftProduct.affiliate_url} onChange={(e) => setDraftProduct({ ...draftProduct, affiliate_url: e.target.value })} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth multiline minRows={2} label="Short description" value={draftProduct.short_description} onChange={(e) => setDraftProduct({ ...draftProduct, short_description: e.target.value })} /></Grid>
                <Grid size={{ xs: 12 }}><Typography fontWeight={800} sx={{ mb: 1 }}>Content</Typography><ClientRichTextEditor value={draftProduct.content} onChange={(content) => setDraftProduct({ ...draftProduct, content })} minHeight={220} /></Grid>
              </Grid>
              <Button variant="contained" onClick={addProduct} sx={{ alignSelf: "flex-start" }}>Add product</Button>
            </Stack>
          ) : null}

          {tab === 2 ? <Stack spacing={2}><TextField fullWidth label="SEO title" inputProps={{ maxLength: 70 }} value={post.seo_title} onChange={(e) => setPost({ ...post, seo_title: e.target.value })} helperText={`${post.seo_title.length}/70`} /><TextField fullWidth multiline minRows={3} label="Meta description" inputProps={{ maxLength: 320 }} value={post.meta_description} onChange={(e) => setPost({ ...post, meta_description: e.target.value })} helperText={`${post.meta_description.length}/320`} /><TextField fullWidth label="Meta keywords" value={post.meta_keywords} onChange={(e) => setPost({ ...post, meta_keywords: e.target.value })} /></Stack> : null}
        </Box>
      </Paper>
    </Stack>
  );
}
