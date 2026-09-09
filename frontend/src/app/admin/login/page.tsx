"use client";

import { Alert, Box, Button, Paper, TextField, Typography } from "@mui/material";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { adminLogin, ensureAdminCsrf } from "@/lib/admin-api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { ensureAdminCsrf().then((session) => { if (session.authenticated) router.replace("/admin"); }).catch(() => undefined); }, [router]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { await adminLogin(username, password); router.replace("/admin"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign in."); }
    finally { setBusy(false); }
  }

  return <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2, bgcolor: "background.default" }}>
    <Paper component="form" onSubmit={submit} variant="outlined" sx={{ width: "100%", maxWidth: 420, p: 4 }}>
      <Typography variant="overline" color="primary" fontWeight={800}>LearnLoot</Typography>
      <Typography variant="h4" fontWeight={900} sx={{ mt: 0.5 }}>Admin sign in</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>Use a Django staff or superuser account.</Typography>
      {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
      <TextField fullWidth label="Username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} sx={{ mb: 2 }} />
      <TextField fullWidth label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} sx={{ mb: 3 }} />
      <Button fullWidth variant="contained" size="large" type="submit" disabled={busy}>{busy ? "Signing in..." : "Sign in"}</Button>
    </Paper>
  </Box>;
}
