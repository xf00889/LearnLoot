import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AdminShell } from "@/components/admin/admin-shell";
import { AdminThemeProvider } from "@/components/admin/admin-theme-provider";

export const metadata: Metadata = {
  title: "Admin",
  robots: { index: false, follow: false, noarchive: true, nocache: true },
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <AdminThemeProvider><AdminShell>{children}</AdminShell></AdminThemeProvider>;
}
