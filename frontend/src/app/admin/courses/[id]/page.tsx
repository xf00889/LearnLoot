"use client";

import { Alert, Box, Button, Divider, Grid, MenuItem, Paper, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import ClientRichTextEditor from "@/components/admin/client-rich-text-editor";
import {
  getAdminCategories,
  getAdminCourse,
  updateAdminCourse,
  uploadCourseImage,
  type AdminCategory,
  type AdminCourseDetail,
} from "@/lib/admin-api";

export default function AdminCourseEditPage() {
  const params = useParams<{ id: string }>();
  const [course, setCourse] = useState<AdminCourseDetail | null>(null);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [tab, setTab] = useState(0);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    Promise.all([getAdminCourse(params.id), getAdminCategories("course")])
      .then(([courseData, categoryData]) => {
        setCourse(courseData);
        setCategories(categoryData.results.filter((category) => category.is_active || category.id === courseData.cms.category?.id));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Unable to load course."));
  }, [params.id]);

  if (!course) return <Stack spacing={2}><Typography variant="h4" fontWeight={900}>Course editor</Typography>{error ? <Alert severity="error">{error}</Alert> : <Typography>Loading...</Typography>}</Stack>;

  async function save() {
    const currentCourse = course;
    if (!currentCourse) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await updateAdminCourse(currentCourse.id, {
        status: currentCourse.status,
        slug: currentCourse.slug,
        editorial_title: currentCourse.cms.editorial_title,
        content: currentCourse.cms.content,
        short_description: currentCourse.cms.short_description,
        category_id: currentCourse.cms.category?.id ?? null,
        language: currentCourse.cms.language ?? "",
        seo_title: currentCourse.cms.seo_title,
        meta_description: currentCourse.cms.meta_description,
        meta_keywords: currentCourse.cms.meta_keywords,
      });
      setCourse(updated);
      setMessage("Course CMS changes saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <div><Typography variant="h4" fontWeight={900}>{course.title}</Typography><Typography color="text.secondary">{course.provider} · source ID {course.external_id}</Typography></div>
        <Button variant="contained" onClick={save} disabled={saving}>{saving ? "Saving..." : "Save changes"}</Button>
      </Stack>
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper variant="outlined">
        <Tabs value={tab} onChange={(_, value) => setTab(value)} variant="scrollable">
          <Tab label="Content" /><Tab label="SEO" /><Tab label="Source data" /><Tab label="Publishing & analytics" />
        </Tabs>
        <Divider />
        <Box sx={{ p: 3 }}>
          {tab === 0 ? (
            <Stack spacing={2.5}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, md: 8 }}><TextField fullWidth label="Public title" value={course.cms.editorial_title} helperText={`Fallback: ${course.source_title}`} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, editorial_title: e.target.value } })} /></Grid>
                <Grid size={{ xs: 12, md: 4 }}><TextField select fullWidth label="Status" value={course.status} onChange={(e) => setCourse({ ...course, status: e.target.value })}><MenuItem value="active">Active</MenuItem><MenuItem value="hidden">Hidden</MenuItem><MenuItem value="archived">Archived</MenuItem></TextField></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth label="Slug" value={course.slug} onChange={(e) => setCourse({ ...course, slug: e.target.value })} /></Grid>
                <Grid size={{ xs: 12, md: 6 }}>
                  <TextField select fullWidth label="Category" value={course.cms.category?.id ?? ""} helperText="Automation leaves this empty. Assign it manually in the CMS." onChange={(e) => { const id = Number(e.target.value); setCourse({ ...course, cms: { ...course.cms, category: categories.find((category) => category.id === id) ?? null } }); }}>
                    <MenuItem value=""><em>No category</em></MenuItem>
                    {categories.map((category) => <MenuItem key={category.id} value={category.id}>{category.name}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid size={{ xs: 12, md: 6 }}><TextField fullWidth label="Language (optional)" value={course.cms.language ?? ""} placeholder="English" onChange={(e) => setCourse({ ...course, cms: { ...course.cms, language: e.target.value || null } })} /></Grid>
                <Grid size={{ xs: 12 }}><TextField fullWidth multiline minRows={2} label="Short description" inputProps={{ maxLength: 500 }} value={course.cms.short_description} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, short_description: e.target.value } })} helperText={`${course.cms.short_description.length}/500`} /></Grid>
              </Grid>

              <div><Typography fontWeight={800} sx={{ mb: 1 }}>Content</Typography><ClientRichTextEditor value={course.cms.content} onChange={(value) => setCourse({ ...course, cms: { ...course.cms, content: value, editorial_description: value } })} /></div>

              <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
                <Button component="label" variant="outlined">Upload public image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; await uploadCourseImage(course.id, "editorial", file); setCourse(await getAdminCourse(course.id)); e.target.value = ""; }} /></Button>
                <Button component="label" variant="outlined">Upload social image<input hidden type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={async (e) => { const file = e.target.files?.[0]; if (!file) return; await uploadCourseImage(course.id, "social", file); setCourse(await getAdminCourse(course.id)); e.target.value = ""; }} /></Button>
                <Typography variant="body2" color="text.secondary">Public image: {course.cms.editorial_image_url || course.source.thumbnail_url || "none"}</Typography>
              </Stack>
            </Stack>
          ) : null}

          {tab === 1 ? <Stack spacing={2}><TextField fullWidth label="SEO title" inputProps={{ maxLength: 70 }} value={course.cms.seo_title} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, seo_title: e.target.value } })} helperText={`${course.cms.seo_title.length}/70`} /><TextField fullWidth multiline minRows={3} label="Meta description" inputProps={{ maxLength: 320 }} value={course.cms.meta_description} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, meta_description: e.target.value } })} helperText={`${course.cms.meta_description.length}/320`} /><TextField fullWidth label="Meta keywords" value={course.cms.meta_keywords} onChange={(e) => setCourse({ ...course, cms: { ...course.cms, meta_keywords: e.target.value } })} /></Stack> : null}

          {tab === 2 ? <Stack spacing={2}><TextField fullWidth label="Scraped title" value={course.source_title} InputProps={{ readOnly: true }} /><TextField fullWidth label="Canonical provider URL" value={course.source.canonical_url} InputProps={{ readOnly: true }} /><TextField fullWidth label="Scraped image URL" value={course.source.thumbnail_url} InputProps={{ readOnly: true }} /><TextField fullWidth label="Instructor" value={course.source.instructor_name} InputProps={{ readOnly: true }} /><TextField fullWidth multiline minRows={4} label="Scraped description" value={course.source.description} InputProps={{ readOnly: true }} /><Typography variant="body2" color="text.secondary">Discovery refreshes only these source fields. Category, language, short description, content, slug and SEO overrides are preserved.</Typography></Stack> : null}

          {tab === 3 ? <Stack spacing={1.5}><Typography>Eligible: {course.publishing.eligible ? "Yes" : "No"}</Typography><Typography>Score: {course.publishing.score ?? "—"}</Typography><Typography>Queue records: {course.publishing.queue_count}</Typography><Typography>Outbound clicks: {course.publishing.click_count}</Typography><Typography color="text.secondary">Reasons: {course.publishing.reasons.join(", ") || "None"}</Typography></Stack> : null}
        </Box>
      </Paper>
    </Stack>
  );
}
