"use client";

import DashboardOutlined from "@mui/icons-material/DashboardOutlined";
import FolderOutlined from "@mui/icons-material/FolderOutlined";
import LogoutOutlined from "@mui/icons-material/LogoutOutlined";
import MenuBookOutlined from "@mui/icons-material/MenuBookOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import OpenInNewOutlined from "@mui/icons-material/OpenInNewOutlined";
import PhotoLibraryOutlined from "@mui/icons-material/PhotoLibraryOutlined";
import ShoppingBagOutlined from "@mui/icons-material/ShoppingBagOutlined";
import {
  AppBar, Box, Button, CircularProgress, Divider, Drawer, IconButton, List,
  ListItemButton, ListItemIcon, ListItemText, Toolbar, Typography,
} from "@mui/material";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { adminLogout, ensureAdminCsrf, type AdminUser } from "@/lib/admin-api";

const drawerWidth = 236;

const sectionGroups = [
  {
    label: "Courses",
    icon: <MenuBookOutlined />,
    hrefs: [
      { href: "/admin/courses", label: "All courses" },
      { href: "/admin/courses/categories", label: "Categories" },
      { href: "/admin/discovery", label: "Discovery runs" },
    ],
  },
  {
    label: "Affiliate",
    icon: <ShoppingBagOutlined />,
    hrefs: [
      { href: "/admin/shop", label: "Content" },
      { href: "/admin/shop/categories", label: "Categories" },
    ],
  },
];

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<AdminUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (pathname === "/admin/login") return;

    let cancelled = false;
    ensureAdminCsrf()
      .then((session) => {
        if (cancelled) return;
        if (!session.authenticated || !session.user) router.replace("/admin/login");
        else setUser(session.user);
      })
      .catch(() => {
        if (!cancelled) router.replace("/admin/login");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [pathname, router]);

  if (pathname === "/admin/login") return <>{children}</>;
  if (loading || !user) return <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center" }}><CircularProgress /></Box>;

  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar sx={{ px: 2 }}><Typography fontWeight={900}>LearnLoot Admin</Typography></Toolbar>
      <Divider />
      <List sx={{ px: 1, py: 1 }}>
        <ListItemButton component={Link} href="/admin" selected={pathname === "/admin"} sx={{ borderRadius: 1, mb: 0.5 }}>
          <ListItemIcon sx={{ minWidth: 38 }}><DashboardOutlined /></ListItemIcon>
          <ListItemText primary="Dashboard" />
        </ListItemButton>

        {sectionGroups.map((group) => (
          <Box key={group.label} sx={{ mb: 0.75 }}>
            <ListItemButton disabled sx={{ opacity: "1 !important", borderRadius: 1, minHeight: 40 }}>
              <ListItemIcon sx={{ minWidth: 38, color: "text.primary" }}>{group.icon}</ListItemIcon>
              <ListItemText primary={group.label} primaryTypographyProps={{ fontWeight: 800, color: "text.primary" }} />
            </ListItemButton>
            <List disablePadding>
              {group.hrefs.map((item) => (
                <ListItemButton
                  key={item.href}
                  component={Link}
                  href={item.href}
                  selected={pathname === item.href || (item.href.endsWith("/courses") && pathname.startsWith("/admin/courses/") && !pathname.startsWith("/admin/courses/categories")) || (item.href.endsWith("/shop") && pathname.startsWith("/admin/shop/") && !pathname.startsWith("/admin/shop/categories"))}
                  sx={{ borderRadius: 1, mb: 0.25, pl: 6.25, minHeight: 38 }}
                >
                  <ListItemText primary={item.label} primaryTypographyProps={{ fontSize: 14 }} />
                </ListItemButton>
              ))}
            </List>
          </Box>
        ))}

        <ListItemButton component={Link} href="/admin/media" selected={pathname === "/admin/media"} sx={{ borderRadius: 1, mb: 0.5 }}>
          <ListItemIcon sx={{ minWidth: 38 }}><PhotoLibraryOutlined /></ListItemIcon>
          <ListItemText primary="Media Library" />
        </ListItemButton>
      </List>
      <Box sx={{ mt: "auto", p: 1 }}>
        <ListItemButton component="a" href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"}`.replace(/\/api\/?$/, "/django-admin/")} sx={{ borderRadius: 1 }}>
          <ListItemIcon sx={{ minWidth: 38 }}><FolderOutlined /></ListItemIcon>
          <ListItemText primary="Django fallback" secondary="Emergency only" />
        </ListItemButton>
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <AppBar position="fixed" elevation={0} color="inherit" sx={{ borderBottom: 1, borderColor: "divider", ml: { md: `${drawerWidth}px` }, width: { md: `calc(100% - ${drawerWidth}px)` } }}>
        <Toolbar>
          <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ display: { md: "none" }, mr: 1 }}><MenuIcon /></IconButton>
          <Typography sx={{ flexGrow: 1, fontWeight: 800 }}>Content management</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mr: 2, display: { xs: "none", sm: "block" } }}>{user.username}</Typography>
          <Button
            component="a"
            href="/"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Preview homepage in a new tab"
            startIcon={<OpenInNewOutlined />}
            color="inherit"
            sx={{ mr: 1, minWidth: { xs: 40, sm: "auto" }, "& .MuiButton-startIcon": { mr: { xs: 0, sm: 1 } } }}
          >
            <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>Preview homepage</Box>
          </Button>
          <Button startIcon={<LogoutOutlined />} color="inherit" onClick={async () => { await adminLogout(); router.replace("/admin/login"); }}>Sign out</Button>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer variant="temporary" open={mobileOpen} onClose={() => setMobileOpen(false)} ModalProps={{ keepMounted: true }} sx={{ display: { xs: "block", md: "none" }, "& .MuiDrawer-paper": { width: drawerWidth } }}>{drawer}</Drawer>
        <Drawer variant="permanent" open sx={{ display: { xs: "none", md: "block" }, "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" } }}>{drawer}</Drawer>
      </Box>
      <Box component="main" sx={{ flexGrow: 1, width: { md: `calc(100% - ${drawerWidth}px)` }, p: { xs: 2, md: 3 }, pt: { xs: 10, md: 11 } }}>{children}</Box>
    </Box>
  );
}
