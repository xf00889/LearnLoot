"use client";

import OpenInNewOutlined from "@mui/icons-material/OpenInNewOutlined";
import PlayArrowOutlined from "@mui/icons-material/PlayArrowOutlined";
import RefreshOutlined from "@mui/icons-material/RefreshOutlined";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  getAdminDiscoveryRun,
  getAdminDiscoveryRuns,
  queueAdminDiscovery,
  type AdminDiscoveryRun,
  type AdminDiscoveryRunDetail,
} from "@/lib/admin-api";

type StatusColor = "default" | "info" | "success" | "error";

function statusColor(status: string): StatusColor {
  if (status === "running") return "info";
  if (status === "succeeded") return "success";
  if (status === "failed") return "error";
  return "default";
}

function statusLabel(status: string): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function displayDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

export default function AdminDiscoveryPage() {
  const [runs, setRuns] = useState<AdminDiscoveryRun[]>([]);
  const [courseCount, setCourseCount] = useState("");
  const [topic, setTopic] = useState("");
  const [runDialogOpen, setRunDialogOpen] = useState(false);
  const [selectedRun, setSelectedRun] = useState<AdminDiscoveryRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [queuing, setQueuing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [runError, setRunError] = useState("");

  const loadRuns = useCallback(async () => {
    try {
      const data = await getAdminDiscoveryRuns();
      setRuns(data.results);
      setCourseCount((current) => current || String(data.filters.default_course_count));
    } catch (value) {
      setError(value instanceof Error ? value.message : "Unable to load discovery runs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initialLoad = window.setTimeout(() => void loadRuns(), 0);
    const timer = window.setInterval(() => void loadRuns(), 10000);
    return () => {
      window.clearTimeout(initialLoad);
      window.clearInterval(timer);
    };
  }, [loadRuns]);

  async function viewRun(id: number) {
    setDetailLoading(true);
    setError("");
    try {
      setSelectedRun(await getAdminDiscoveryRun(id));
    } catch (value) {
      setError(value instanceof Error ? value.message : "Unable to load discovery results.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function refresh() {
    setRefreshing(true);
    setError("");
    await loadRuns();
    if (selectedRun) await viewRun(selectedRun.id);
    setRefreshing(false);
  }

  async function runScraper() {
    const requestedCount = Number(courseCount);
    if (!Number.isInteger(requestedCount) || requestedCount < 1 || requestedCount > 5000) {
      setRunError("Enter a whole number between 1 and 5000.");
      return;
    }
    setQueuing(true);
    setError("");
    setRunError("");
    setMessage("");
    try {
      const result = await queueAdminDiscovery(requestedCount, topic);
      setMessage(result.worker_started
        ? `A local Celery worker was started for ${result.search_filters.label}. LearnLoot will skip courses already stored and continue looking for up to ${result.course_count} new courses.`
        : `Queued ${result.search_filters.label}. LearnLoot will skip courses already stored and continue looking for up to ${result.course_count} new courses.`);
      setRunDialogOpen(false);
      await loadRuns();
    } catch (value) {
      setRunError(value instanceof Error ? value.message : "Unable to queue discovery.");
    } finally {
      setQueuing(false);
    }
  }

  const stats = selectedRun ? [
    ["Seen", selectedRun.records_found],
    ["Created", selectedRun.records_new],
    ["Updated", selectedRun.records_updated],
    ["Rejected", selectedRun.records_failed],
  ] : [];
  const parsedCourseCount = Number(courseCount);
  const courseCountIsValid = Number.isInteger(parsedCourseCount) && parsedCourseCount >= 1 && parsedCourseCount <= 5000;

  return (
    <Stack spacing={2.5}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <div>
          <Typography variant="h4" fontWeight={900}>Discovery runs</Typography>
          <Typography color="text.secondary">Run the Udemy scraper and review its persisted results after Celery processes the task.</Typography>
        </div>
        <Stack direction="row" gap={1} alignItems="flex-start">
          <Button variant="outlined" startIcon={<RefreshOutlined />} onClick={refresh} disabled={refreshing}>
            {refreshing ? "Refreshing..." : "Refresh"}
          </Button>
          <Button variant="contained" startIcon={<PlayArrowOutlined />} onClick={() => {
            setRunError("");
            setRunDialogOpen(true);
          }} disabled={queuing}>
            Run scraper now
          </Button>
        </Stack>
      </Stack>

      {message ? <Alert severity="success">{message}</Alert> : null}
      {error ? <Alert severity="error">{error}</Alert> : null}

      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small" sx={{ minWidth: 1080 }}>
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell><TableCell>Search filters</TableCell><TableCell>Status</TableCell><TableCell>Started</TableCell><TableCell>Finished</TableCell>
              <TableCell>Seen</TableCell><TableCell>Created</TableCell><TableCell>Updated</TableCell><TableCell>Rejected</TableCell><TableCell align="right">Action</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} hover selected={selectedRun?.id === run.id}>
                <TableCell><Typography fontWeight={700}>{run.provider.name}</Typography></TableCell>
                <TableCell>{run.search_filters.label}</TableCell>
                <TableCell><Chip size="small" color={statusColor(run.status)} label={statusLabel(run.status)} variant="outlined" /></TableCell>
                <TableCell>{displayDate(run.started_at)}</TableCell>
                <TableCell>{displayDate(run.finished_at)}</TableCell>
                <TableCell>{run.records_found}</TableCell>
                <TableCell>{run.records_new}</TableCell>
                <TableCell>{run.records_updated}</TableCell>
                <TableCell>{run.records_failed}</TableCell>
                <TableCell align="right"><Button size="small" onClick={() => viewRun(run.id)}>View</Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {loading ? <Box sx={{ p: 3, display: "flex", justifyContent: "center" }}><CircularProgress size={24} /></Box> : null}
        {!loading && runs.length === 0 ? <Typography color="text.secondary" sx={{ p: 3 }}>No discovery runs yet. Queue the scraper to create the first run.</Typography> : null}
      </Paper>

      {detailLoading ? <Box sx={{ py: 3, display: "flex", justifyContent: "center" }}><CircularProgress /></Box> : null}
      {selectedRun && !detailLoading ? (
        <Paper variant="outlined" sx={{ overflow: "hidden" }}>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ p: 2, borderBottom: 1, borderColor: "divider" }}>
            <div>
              <Typography variant="h6" fontWeight={900}>Run #{selectedRun.id}</Typography>
              <Typography variant="body2" color="text.secondary">{selectedRun.provider.name} · {selectedRun.search_filters.label} · {displayDate(selectedRun.started_at)}</Typography>
            </div>
            <Chip size="small" color={statusColor(selectedRun.status)} label={statusLabel(selectedRun.status)} variant="outlined" sx={{ alignSelf: "flex-start" }} />
          </Stack>

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "repeat(2, 1fr)", sm: "repeat(4, 1fr)" }, borderBottom: 1, borderColor: "divider" }}>
            {stats.map(([label, value]) => <Box key={String(label)} sx={{ p: 2, borderRight: 1, borderColor: "divider" }}><Typography variant="caption" color="text.secondary">{label}</Typography><Typography variant="h5" fontWeight={900}>{value}</Typography></Box>)}
          </Box>

          {selectedRun.error_message ? <Alert severity="error" sx={{ borderRadius: 0 }}>{selectedRun.error_message}</Alert> : null}

          <Box sx={{ overflowX: "auto" }}>
            <Table size="small" sx={{ minWidth: 760 }}>
              <TableHead><TableRow><TableCell>Course</TableCell><TableCell>External ID</TableCell><TableCell>Source</TableCell><TableCell>Observed</TableCell><TableCell align="right">Action</TableCell></TableRow></TableHead>
              <TableBody>
                {selectedRun.observations.results.map((observation) => (
                  <TableRow key={observation.id} hover>
                    <TableCell>{observation.course ? <Typography fontWeight={700}>{observation.course.title}</Typography> : <Chip size="small" color="error" label="Rejected" variant="outlined" />}</TableCell>
                    <TableCell>{observation.external_id || "—"}</TableCell>
                    <TableCell><Button component="a" href={observation.source_url} target="_blank" rel="noopener noreferrer" size="small" startIcon={<OpenInNewOutlined />}>Source</Button></TableCell>
                    <TableCell>{displayDate(observation.observed_at)}</TableCell>
                    <TableCell align="right">{observation.course ? <Button component={Link} href={`/admin/courses/${observation.course.id}`} size="small">View course</Button> : "—"}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
          {selectedRun.observations.results.length === 0 ? <Typography color="text.secondary" sx={{ p: 3 }}>This run has no observations yet.</Typography> : null}
          {selectedRun.observations.count > selectedRun.observations.results.length ? <Typography variant="caption" color="text.secondary" sx={{ display: "block", px: 2, py: 1.5 }}>Showing the first {selectedRun.observations.results.length} of {selectedRun.observations.count} observations.</Typography> : null}
        </Paper>
      ) : null}

      <Dialog open={runDialogOpen} onClose={queuing ? undefined : () => setRunDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Run Udemy scraper</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>Choose an optional Udemy topic. LearnLoot uses robots-compatible public free-topic pages instead of blocked search URL facets.</DialogContentText>
          {runError ? <Alert severity="error" sx={{ mb: 2 }}>{runError}</Alert> : null}
          <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mb: 2 }}>
            <Chip size="small" color="success" variant="outlined" label="Price: Free" />
            <Chip size="small" color="info" variant="outlined" label="Language: English" />
            <Chip size="small" variant="outlined" label="Certification Prep: later" />
          </Stack>
          <Stack spacing={2}>
            <TextField
              fullWidth
              autoFocus
              label="Topic"
              placeholder="Python, SQL, JavaScript..."
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              helperText="Leave blank for all free topics. For example, Python uses /topic/python/free/ rather than /courses/search/?..."
            />
            <TextField
              fullWidth
              type="number"
              label="Number of new courses to scrape"
              value={courseCount}
              onChange={(event) => setCourseCount(event.target.value)}
              error={courseCount !== "" && !courseCountIsValid}
              helperText="Enter 1 to 5000. Courses already stored in LearnLoot are skipped before this limit is counted."
              slotProps={{ htmlInput: { min: 1, max: 5000, step: 1 } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRunDialogOpen(false)} disabled={queuing}>Cancel</Button>
          <Button variant="contained" startIcon={<PlayArrowOutlined />} onClick={runScraper} disabled={queuing || !courseCountIsValid}>
            {queuing ? "Queuing..." : "Run scraper"}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
