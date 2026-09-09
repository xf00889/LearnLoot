"use client";

import { Alert, Box, Button, Chip, Divider, Grid, MenuItem, Paper, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ClientRichTextEditor from "@/components/admin/client-rich-text-editor";
import { getAdminCourse, updateAdminCourse, uploadCourseImage, type AdminCourseDetail } from "@/lib/admin-api";

export default function AdminCourseEditPage() {
  const params = useParams<{ id: string }>();
  const [course, setCourse] = useState<AdminCourseDetail | null>(null);
  const [tab, setTab] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { getAdminCourse(params.id).then(setCourse).catch((e) => setError(e instanceof Error ? e.message : "Unable to load course.")); }, [params.id]);
  if (!course) return <Stack spacing={2}><Typography variant="h4" fontWeight={900}>Course editor</Typography>{error ? <Alert severity="error">{error}</Alert> : <Typography>Loading...</Typography>}</Stack>;

  async function save() {
    const currentCourse = course;
    if (!currentCourse) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await updateAdminCourse(currentCourse.id, { status: currentCourse.status, slug: currentCourse.slug, editorial_title: currentCourse.cms.editorial_title, editorial_description: currentCourse.cms.editorial_description, seo_title: currentCourse.cms.seo_title, meta_description: currentCourse.cms.meta_description, meta_keywords: currentCourse.cms.meta_keywords });
      setCourse(updated); setMessage("Course CMS changes saved.");
    } catch (e) { setError(e instanceof Error ? e.message : "Save failed."); } finally { setSaving(false); }
  }

  return <Stack spacing={2}>
    <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}><div><Typography variant="h4" fontWeight={900}>{course.title}</Typography><Typography color="text.secondary">{course.provider} · source ID {course.external_id}</Typography></div><Button variant="contained" onClick={save} disabled={saving}>{saving ? "Saving..." : "Save changes"}</Button></Stack>
    {message ? <Alert severity="success">{message}</Alert> : null}{error ? <Alert severity="error">{error}</Alert> : null}
    <Paper variant="outlined"><Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable"><Tab label="Content" /><Tab label="SEO" /><Tab label="Source data" /><Tab label="Publishing & analytics" /></Tabs><Divider />
      <Box sx={{ p: 3 }}>
        {tab === 0 ? <Stack spacing={2}><Grid container spacing={2}><Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="Public title" value={course.cms.editorial_title} helperText={`Fallback: ${course.source_title}`} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, editorial_title: e.target.value } })} /></Grid><Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Status" value={course.status} onChange={(e) => setCourse({ ...course, status: e.target.value })}><MenuItem value="active">Active</MenuItem><MenuItem value="hidden">Hidden</MenuItem><MenuItem value="archived">Archived</MenuItem></TextField></Grid><Grid size={{ xs: 12 }}><TextField fullWidth label="Slug" value={course.slug} onChange={(e) => setCourse({ ...course, slug: e.target.value })} /></Grid></Grid><div><Typography fontWeight={800} sx={{ mb: 1 }}>Editorial content</Typography><ClientRichTextEditor value={course.cms.editorial_description} onChange={(value) => setCourse({ ...course, cms: { ...course.cms, editorial_description: value } })} /></div><Stack direction="row" gap={1} alignItems="center"><Button component="label" variant="outlined">Upload public image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; const result = await uploadCourseImage(course.id, "editorial", file); setCourse({ ...course, cms: { ...course.cms, editorial_image_url: result.url } }); e.target.value = ""; }} /></Button>{course.cms.editorial_image_url ? <Typography variant="caption" color="text.secondary">Public image configured</Typography> : null}</Stack></Stack> : null}
        {tab === 1 ? <Stack spacing={2}><TextField fullWidth label="SEO title" inputProps={{ maxLength: 70 }} value={course.cms.seo_title} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, seo_title: e.target.value } })} helperText={`${course.cms.seo_title.length}/70`} /><TextField fullWidth multiline minRows={3} label="Meta description" inputProps={{ maxLength: 320 }} value={course.cms.meta_description} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, meta_description: e.target.value } })} helperText={`${course.cms.meta_description.length}/320`} /><TextField fullWidth label="Meta keywords" value={course.cms.meta_keywords} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, meta_keywords: e.target.value } })} /><Stack direction="row" gap={1} alignItems="center"><Button component="label" variant="outlined">Upload social image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; const result = await uploadCourseImage(course.id, "social", file); setCourse({ ...course, cms: { ...course.cms, social_image_url: result.url } }); e.target.value = ""; }} /></Button>{course.cms.social_image_url ? <Typography variant="caption" color="text.secondary">Social image configured</Typography> : null}</Stack></Stack> : null}
        {tab === 2 ? <Stack spacing={2}><Alert severity="info">These fields come from discovery and are read-only here. Use the CMS overrides instead.</Alert><TextField fullWidth label="Canonical provider URL" value={course.source.canonical_url} InputProps={{ readOnly: true }} /><TextField fullWidth label="Instructor" value={course.source.instructor_name} InputProps={{ readOnly: true }} /><TextField fullWidth multiline minRows={6} label="Scraped description" value={course.source.description} InputProps={{ readOnly: true }} /><Typography variant="body2" color="text.secondary">Rating {course.rating ?? "—"} · Reviews {course.review_count?.toLocaleString() ?? "—"} · Students {course.source.student_count?.toLocaleString() ?? "—"}</Typography></Stack> : null}
        {tab === 3 ? <Stack spacing={2}><Stack direction="row" gap={1} flexWrap="wrap"><Chip label={course.publishing.eligible ? "Eligible" : "Not eligible"} color={course.publishing.eligible ? "success" : "default"} /><Chip label={`Score ${course.publishing.score ?? "—"}`} /><Chip label={`${course.publishing.click_count} clicks`} /><Chip label={`${course.publishing.queue_count} queue records`} /></Stack><Typography fontWeight={800}>Eligibility reasons</Typography><Typography color="text.secondary">{course.publishing.reasons.length ? course.publishing.reasons.join(", ") : "No reasons recorded."}</Typography><Typography fontWeight={800}>Recent price history</Typography>{course.prices.map((price) => <Typography variant="body2" key={price.observed_at}>{new Date(price.observed_at).toLocaleString()} · {price.is_free ? "Free" : `${price.amount ?? "—"} ${price.currency}`} · {price.price_type}</Typography>)}</Stack> : null}
      </Box>
    </Paper>
  </Stack>;
}
