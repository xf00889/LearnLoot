const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type AdminUser = { id: number; username: string; email: string; is_staff: boolean; is_superuser: boolean };
export type AdminSession = { authenticated: boolean; user: AdminUser | null };

export type AdminCategoryScope = "course" | "affiliate";
export type AdminCategory = {
  id: number;
  scope: AdminCategoryScope;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  updated_at: string;
};

export type DashboardPayload = {
  courses: { total: number; active: number; customized: number };
  shopping: { posts: number; published: number; products: number };
  analytics: { course_clicks: number; shopping_clicks: number };
  publishing: { queued: number; telegram_failed: number };
  media: { assets: number };
  categories: { courses: number; affiliate: number };
  discovery: { latest_status: string | null; latest_started_at: string | null };
};

export type AdminDiscoveryProvider = { id: number; name: string; slug: string };
export type AdminDiscoverySearchFilters = { label: string; query: string; topic: string; language: string; price: string; certification_only: boolean };
export type AdminDiscoveryRun = {
  id: number;
  provider: AdminDiscoveryProvider;
  search_filters: AdminDiscoverySearchFilters;
  source: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  records_found: number;
  records_new: number;
  records_updated: number;
  records_failed: number;
  error_message: string;
};
export type AdminDiscoveryObservation = {
  id: number;
  external_id: string;
  source_url: string;
  observed_at: string;
  course: { id: number; title: string } | null;
};
export type AdminDiscoveryRunDetail = AdminDiscoveryRun & {
  observations: { count: number; results: AdminDiscoveryObservation[] };
};

export type AdminCourseSummary = {
  id: number;
  title: string;
  source_title: string;
  provider: string;
  provider_slug: string;
  external_id: string;
  slug: string;
  status: string;
  thumbnail_url: string;
  category: AdminCategory | null;
  language: string | null;
  short_description: string;
  rating: string | null;
  review_count: number | null;
  last_checked_at: string | null;
  customized: boolean;
  updated_at: string;
};

export type AdminCourseDetail = AdminCourseSummary & {
  cms: {
    editorial_title: string;
    editorial_description: string;
    content: string;
    short_description: string;
    category: AdminCategory | null;
    language: string | null;
    editorial_image_url: string;
    seo_title: string;
    meta_description: string;
    meta_keywords: string;
    social_image_url: string;
  };
  source: {
    canonical_url: string;
    thumbnail_url: string;
    instructor_name: string;
    description: string;
    student_count: number | null;
    duration_minutes: number | null;
    first_seen_at: string;
    last_seen_at: string;
  };
  prices: Array<{ amount: string | null; currency: string; is_free: boolean; price_type: string; observed_at: string }>;
  publishing: { eligible: boolean; score: number | null; reasons: string[]; evaluated_at: string | null; queue_count: number; click_count: number };
};

export type AdminShoppingPostSummary = {
  id: number;
  title: string;
  slug: string;
  post_type: string;
  status: string;
  category: AdminCategory | null;
  language: string | null;
  short_description: string;
  is_featured: boolean;
  published_at: string | null;
  updated_at: string;
  product_count: number;
};

export type AdminShoppingProduct = {
  id: number;
  position: number;
  name: string;
  slug: string;
  image_url: string;
  short_description: string;
  content: string;
  category: AdminCategory | null;
  language: string | null;
  affiliate_url: string;
  displayed_price: string;
  original_price: string;
  currency: string;
  badge: string;
  pros: string;
  cons: string;
  is_active: boolean;
  expires_at: string | null;
};

export type AdminShoppingPostDetail = AdminShoppingPostSummary & {
  excerpt: string;
  body: string;
  content: string;
  cover_image_url: string;
  seo_title: string;
  meta_description: string;
  meta_keywords: string;
  products: AdminShoppingProduct[];
};

export type MediaAsset = { id: number; url: string; name: string; title: string; alt_text: string; content_type: string; size_bytes: number; created_at: string };

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!(options.body instanceof FormData) && options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) headers.set("X-CSRFToken", csrfToken());
  const response = await fetch(`${API_BASE_URL}/admin${path}`, { ...options, headers, credentials: "include", cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail ?? payload.error ?? payload);
    const error = new Error(detail || `Admin API request failed (${response.status})`);
    Object.assign(error, { status: response.status });
    throw error;
  }
  return payload as T;
}

export async function ensureAdminCsrf(): Promise<AdminSession> { return request<AdminSession>("/auth/session/"); }
export async function adminLogin(username: string, password: string): Promise<AdminSession> { await ensureAdminCsrf(); return request<AdminSession>("/auth/login/", { method: "POST", body: JSON.stringify({ username, password }) }); }
export async function adminLogout(): Promise<void> { await request("/auth/logout/", { method: "POST", body: "{}" }); }
export async function getDashboard(): Promise<DashboardPayload> { return request("/dashboard/"); }
export async function getAdminDiscoveryRuns(): Promise<{ count: number; results: AdminDiscoveryRun[]; filters: { default_course_count: number } }> { return request("/discovery/runs/"); }
export async function getAdminDiscoveryRun(id: string | number): Promise<AdminDiscoveryRunDetail> { return request(`/discovery/runs/${id}/`); }
export async function queueAdminDiscovery(courseCount: number): Promise<{ queued: boolean; task_id: string; worker_started: boolean; course_count: number; provider: AdminDiscoveryProvider; source_url: string; search_filters: AdminDiscoverySearchFilters }> { return request("/discovery/runs/queue/", { method: "POST", body: JSON.stringify({ course_count: courseCount }) }); }

export async function getAdminCategories(scope: AdminCategoryScope): Promise<{ count: number; results: AdminCategory[] }> {
  return request(`/categories/?scope=${encodeURIComponent(scope)}`);
}
export async function createAdminCategory(scope: AdminCategoryScope, payload: Record<string, unknown>): Promise<AdminCategory> {
  return request(`/categories/?scope=${encodeURIComponent(scope)}`, { method: "POST", body: JSON.stringify(payload) });
}
export async function updateAdminCategory(id: string | number, payload: Record<string, unknown>): Promise<AdminCategory> {
  return request(`/categories/${id}/`, { method: "PATCH", body: JSON.stringify(payload) });
}
export async function deleteAdminCategory(id: string | number): Promise<void> { await request(`/categories/${id}/`, { method: "DELETE", body: "{}" }); }

export async function getAdminCourses(q = ""): Promise<{ count: number; results: AdminCourseSummary[] }> { return request(`/courses/${q ? `?q=${encodeURIComponent(q)}` : ""}`); }
export async function getAdminCourse(id: string | number): Promise<AdminCourseDetail> { return request(`/courses/${id}/`); }
export async function updateAdminCourse(id: string | number, payload: Record<string, unknown>): Promise<AdminCourseDetail> { return request(`/courses/${id}/`, { method: "PATCH", body: JSON.stringify(payload) }); }

export async function getAdminShoppingPosts(q = ""): Promise<{ count: number; results: AdminShoppingPostSummary[] }> { return request(`/shop/posts/${q ? `?q=${encodeURIComponent(q)}` : ""}`); }
export async function createAdminShoppingPost(payload: Record<string, unknown>): Promise<AdminShoppingPostDetail> { return request("/shop/posts/", { method: "POST", body: JSON.stringify(payload) }); }
export async function getAdminShoppingPost(id: string | number): Promise<AdminShoppingPostDetail> { return request(`/shop/posts/${id}/`); }
export async function updateAdminShoppingPost(id: string | number, payload: Record<string, unknown>): Promise<AdminShoppingPostDetail> { return request(`/shop/posts/${id}/`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function createAdminShoppingProduct(postId: string | number, payload: Record<string, unknown>): Promise<AdminShoppingProduct> { return request(`/shop/posts/${postId}/products/`, { method: "POST", body: JSON.stringify(payload) }); }
export async function updateAdminShoppingProduct(id: string | number, payload: Record<string, unknown>): Promise<AdminShoppingProduct> { return request(`/shop/products/${id}/`, { method: "PATCH", body: JSON.stringify(payload) }); }
export async function deleteAdminShoppingProduct(id: string | number): Promise<void> { await request(`/shop/products/${id}/`, { method: "DELETE", body: "{}" }); }

async function uploadTo(path: string, file: File): Promise<{ url: string }> { const body = new FormData(); body.append("upload", file); return request(path, { method: "POST", body }); }
export async function uploadCourseImage(id: string | number, kind: "editorial" | "social", file: File): Promise<{ url: string }> { return uploadTo(`/courses/${id}/images/${kind}/`, file); }
export async function uploadShoppingPostCover(id: string | number, file: File): Promise<{ url: string }> { return uploadTo(`/shop/posts/${id}/cover/`, file); }
export async function uploadShoppingProductImage(id: string | number, file: File): Promise<{ url: string }> { return uploadTo(`/shop/products/${id}/image/`, file); }

export async function getMediaAssets(): Promise<{ count: number; results: MediaAsset[] }> { return request("/media/"); }
export async function uploadMedia(file: File, title = "", altText = ""): Promise<{ id: number; url: string }> { const body = new FormData(); body.append("upload", file); body.append("title", title); body.append("alt_text", altText); return request("/media/", { method: "POST", body }); }
export async function deleteMedia(id: number): Promise<void> { await request(`/media/${id}/`, { method: "DELETE", body: "{}" }); }
export function adminMediaUploadUrl(): string { return `${API_BASE_URL}/admin/media/`; }
export function currentCsrfToken(): string { return csrfToken(); }
