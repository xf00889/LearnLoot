"use client";

import { CssBaseline, ThemeProvider, createTheme, useMediaQuery } from "@mui/material";
import type { ReactNode } from "react";
import { useMemo } from "react";

export function AdminThemeProvider({ children }: { children: ReactNode }) {
  const prefersDark = useMediaQuery("(prefers-color-scheme: dark)");
  const theme = useMemo(() => createTheme({
    palette: {
      mode: prefersDark ? "dark" : "light",
      primary: { main: "#f97316" },
      background: prefersDark ? { default: "#111315", paper: "#181b1f" } : { default: "#f5f6f8", paper: "#ffffff" },
    },
    shape: { borderRadius: 4 },
    typography: { fontFamily: "var(--font-geist-sans), Arial, sans-serif" },
    components: {
      MuiButton: { styleOverrides: { root: { borderRadius: 4, textTransform: "none", fontWeight: 700 } } },
      MuiPaper: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiCard: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiOutlinedInput: { styleOverrides: { root: { borderRadius: 4 } } },
      MuiChip: { styleOverrides: { root: { borderRadius: 4, fontWeight: 700 } } },
      MuiDialog: { styleOverrides: { paper: { borderRadius: 6 } } },
    },
  }), [prefersDark]);

  return <ThemeProvider theme={theme}><CssBaseline />{children}</ThemeProvider>;
}
