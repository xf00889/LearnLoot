"use client";
/* eslint-disable @next/next/no-img-element */

import { Button, Chip, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getAdminCourses, type AdminCourseSummary } from "@/lib/admin-api";

export default function AdminCoursesPage() {
  const [rows, setRows] = useState<AdminCourseSummary[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setLoading(true);
      getAdminCourses(q).then((data) => setRows(data.results)).finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [q]);

  return (
    <Stack spacing={2}>
      <div>
        <Typography variant="h4" fontWeight={900}>Courses</Typography>
        <Typography color="text.secondary">Scraped Udemy records with persistent CMS, taxonomy, image, and SEO overrides.</Typography>
      </div>
      <TextField size="small" label="Search courses" value={q} onChange={(e) => setQ(e.target.value)} sx={{ maxWidth: 420 }} />
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead><TableRow><TableCell>Image</TableCell><TableCell>Course</TableCell><TableCell>Category</TableCell><TableCell>Language</TableCell><TableCell>Status</TableCell><TableCell>Rating</TableCell><TableCell>Last checked</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell sx={{ width: 96 }}>
                  {row.thumbnail_url ? <img alt="" src={row.thumbnail_url} className="h-12 w-20 rounded object-cover" /> : <div className="h-12 w-20 rounded bg-black/5 dark:bg-white/5" />}
                </TableCell>
                <TableCell><Typography fontWeight={700}>{row.title}</Typography><Typography variant="caption" color="text.secondary">{row.customized ? "CMS customized" : "Using scraped content"}</Typography></TableCell>
                <TableCell>{row.category?.name ?? "—"}</TableCell>
                <TableCell>{row.language ?? "—"}</TableCell>
                <TableCell><Chip label={row.status} size="small" /></TableCell>
                <TableCell>{row.rating ?? "—"}</TableCell>
                <TableCell>{row.last_checked_at ? new Date(row.last_checked_at).toLocaleString() : "—"}</TableCell>
                <TableCell align="right"><Button component={Link} href={`/admin/courses/${row.id}`} size="small">Edit</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {!loading && rows.length === 0 ? <Typography color="text.secondary" sx={{ p: 3 }}>No courses found.</Typography> : null}
      </Paper>
    </Stack>
  );
}
