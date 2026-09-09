"use client";

import { Button, Chip, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getAdminShoppingPosts, type AdminShoppingPostSummary } from "@/lib/admin-api";

export default function AdminShopPage() {
  const [rows, setRows] = useState<AdminShoppingPostSummary[]>([]);
  const [q, setQ] = useState("");
  useEffect(() => { const timer = setTimeout(() => getAdminShoppingPosts(q).then((data) => setRows(data.results)), 250); return () => clearTimeout(timer); }, [q]);

  return (
    <Stack spacing={2}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}><div><Typography variant="h4" fontWeight={900}>Affiliate content</Typography><Typography color="text.secondary">Manual Shopee affiliate posts, rankings, guides, and flash deals.</Typography></div><Button component={Link} href="/admin/shop/new" variant="contained">New content</Button></Stack>
      <TextField size="small" label="Search affiliate content" value={q} onChange={(e) => setQ(e.target.value)} sx={{ maxWidth: 420 }} />
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small"><TableHead><TableRow><TableCell>Title</TableCell><TableCell>Category</TableCell><TableCell>Language</TableCell><TableCell>Type</TableCell><TableCell>Status</TableCell><TableCell>Products</TableCell><TableCell>Updated</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead><TableBody>{rows.map((row) => <TableRow key={row.id} hover><TableCell><Typography fontWeight={700}>{row.title}</Typography><Typography variant="caption" color="text.secondary">/{row.slug}</Typography></TableCell><TableCell>{row.category?.name ?? "—"}</TableCell><TableCell>{row.language ?? "—"}</TableCell><TableCell>{row.post_type}</TableCell><TableCell><Chip size="small" label={row.status} /></TableCell><TableCell>{row.product_count}</TableCell><TableCell>{new Date(row.updated_at).toLocaleString()}</TableCell><TableCell align="right"><Button component={Link} href={`/admin/shop/${row.id}`} size="small">Edit</Button></TableCell></TableRow>)}</TableBody></Table>
      </Paper>
    </Stack>
  );
}
