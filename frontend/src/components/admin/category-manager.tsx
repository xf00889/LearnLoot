"use client";

import { Alert, Button, Chip, Paper, Stack, Switch, Table, TableBody, TableCell, TableHead, TableRow, TextField, Typography } from "@mui/material";
import { useCallback, useEffect, useState } from "react";
import {
  createAdminCategory,
  deleteAdminCategory,
  getAdminCategories,
  updateAdminCategory,
  type AdminCategory,
  type AdminCategoryScope,
} from "@/lib/admin-api";

type CategoryManagerProps = {
  scope: AdminCategoryScope;
  title: string;
  description: string;
};

const emptyDraft = { name: "", slug: "", description: "" };

export function CategoryManager({ scope, title, description }: CategoryManagerProps) {
  const [rows, setRows] = useState<AdminCategory[]>([]);
  const [draft, setDraft] = useState(emptyDraft);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const data = await getAdminCategories(scope);
    setRows(data.results);
  }, [scope]);

  useEffect(() => {
    let cancelled = false;

    getAdminCategories(scope)
      .then((data) => {
        if (!cancelled) setRows(data.results);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : "Unable to load categories.");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [scope]);

  async function createCategory() {
    if (!draft.name.trim()) return;
    setBusy(true); setError(""); setMessage("");
    try {
      await createAdminCategory(scope, draft);
      setDraft(emptyDraft);
      await load();
      setMessage("Category created.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to create category.");
    } finally {
      setBusy(false);
    }
  }

  async function saveCategory(category: AdminCategory) {
    setError(""); setMessage("");
    try {
      const updated = await updateAdminCategory(category.id, {
        name: category.name,
        slug: category.slug,
        description: category.description,
        is_active: category.is_active,
      });
      setRows((current) => current.map((row) => row.id === updated.id ? updated : row));
      setMessage("Category saved.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to save category.");
    }
  }

  async function removeCategory(category: AdminCategory) {
    if (!window.confirm(`Delete category "${category.name}"? Existing content will keep working and its category will become empty.`)) return;
    setError(""); setMessage("");
    try {
      await deleteAdminCategory(category.id);
      await load();
      setMessage("Category deleted.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to delete category.");
    }
  }

  return (
    <Stack spacing={2.5}>
      <div>
        <Typography variant="h4" fontWeight={900}>{title}</Typography>
        <Typography color="text.secondary">{description}</Typography>
      </div>
      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper variant="outlined" sx={{ p: 2.5 }}>
        <Typography variant="h6" fontWeight={900}>Create category</Typography>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ mt: 2 }}>
          <TextField label="Name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} fullWidth />
          <TextField label="Slug (optional)" value={draft.slug} onChange={(e) => setDraft({ ...draft, slug: e.target.value })} fullWidth />
          <TextField label="Description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} fullWidth />
          <Button variant="contained" onClick={createCategory} disabled={busy || !draft.name.trim()} sx={{ minWidth: 130 }}>Create</Button>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead><TableRow><TableCell>Name</TableCell><TableCell>Slug</TableCell><TableCell>Description</TableCell><TableCell>Status</TableCell><TableCell align="right">Actions</TableCell></TableRow></TableHead>
          <TableBody>
            {rows.map((row, index) => (
              <TableRow key={row.id} hover>
                <TableCell sx={{ minWidth: 190 }}><TextField size="small" value={row.name} onChange={(e) => { const next = [...rows]; next[index] = { ...row, name: e.target.value }; setRows(next); }} /></TableCell>
                <TableCell sx={{ minWidth: 190 }}><TextField size="small" value={row.slug} onChange={(e) => { const next = [...rows]; next[index] = { ...row, slug: e.target.value }; setRows(next); }} /></TableCell>
                <TableCell sx={{ minWidth: 260 }}><TextField size="small" fullWidth value={row.description} onChange={(e) => { const next = [...rows]; next[index] = { ...row, description: e.target.value }; setRows(next); }} /></TableCell>
                <TableCell>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Switch size="small" checked={row.is_active} onChange={(e) => { const next = [...rows]; next[index] = { ...row, is_active: e.target.checked }; setRows(next); }} />
                    <Chip size="small" label={row.is_active ? "Active" : "Inactive"} />
                  </Stack>
                </TableCell>
                <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Button size="small" onClick={() => saveCategory(rows[index])}>Save</Button>
                  <Button size="small" color="error" onClick={() => removeCategory(rows[index])}>Delete</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {rows.length === 0 ? <Typography color="text.secondary" sx={{ p: 3 }}>No categories yet. Automation intentionally leaves category empty until you assign one.</Typography> : null}
      </Paper>
    </Stack>
  );
}
