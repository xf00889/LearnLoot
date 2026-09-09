const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type HealthResponse = {
  status: string;
  database: string;
};

export type ProviderSummary = {
  slug: string;
  name: string;
};

export type PublicCategory = {
  name: string;
  slug: string;
};

export type CoursePrice = {
  amount: string | null;
  currency: string;
  is_free: boolean;
  price_type: string;
  observed_at: string;
};

export type SeoPayload = {
  title: string;
  description: string;
  keywords: string;
  social_image_url: string;
};

export type CourseSummary = {
  id: number;
  provider: ProviderSummary;
  title: string;
  slug: string;
  url: string;
  outbound_url: string;
  thumbnail_url: string;
  short_description: string;
  category: PublicCategory | null;
  language: string | null;
  instructor_name: string;
  rating: string | null;
  review_count: number | null;
  student_count: number | null;
  duration_minutes: number | null;
  score: number;
  last_checked_at: string | null;
  latest_price: CoursePrice | null;
};

export type CourseDetail = CourseSummary & {
  description: string;
  description_html: string;
  first_seen_at: string;
  last_seen_at: string;
  eligibility: {
    score: number;
    evaluated_at: string;
  };
  seo: SeoPayload;
};

export type CourseListResponse = {
  generated_at: string;
  count: number;
  results: CourseSummary[];
};

export type ShoppingPostType =
  | "top_10"
  | "flash_deals"
  | "buying_guide"
  | "roundup"
  | "article";

export type ShoppingPostSummary = {
  id: number;
  post_type: ShoppingPostType;
  post_type_label: string;
  title: string;
  slug: string;
  url: string;
  excerpt: string;
  short_description: string;
  category: PublicCategory | null;
  language: string | null;
  cover_image_url: string;
  is_featured: boolean;
  published_at: string | null;
  updated_at: string;
};

export type ShoppingProduct = {
  id: number;
  position: number;
  name: string;
  slug: string;
  image_url: string;
  short_description: string;
  content: string;
  category: PublicCategory | null;
  language: string | null;
  displayed_price: string | null;
  original_price: string | null;
  currency: string;
  badge: string;
  pros: string;
  cons: string;
  expires_at: string | null;
  outbound_url: string;
};

export type ShoppingPostDetail = ShoppingPostSummary & {
  body: string;
  affiliate_disclosure: string;
  seo: SeoPayload;
  products: ShoppingProduct[];
};

export type ShoppingPostListResponse = {
  generated_at: string;
  count: number;
  results: ShoppingPostSummary[];
};

export type SitemapEntry = {
  url: string;
  last_modified: string;
};

export type SitemapResponse = {
  results: SitemapEntry[];
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health/");
}

export async function getCourses(options?: {
  limit?: number;
  q?: string;
}): Promise<CourseListResponse> {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.q) params.set("q", options.q);
  const suffix = params.size ? `?${params.toString()}` : "";
  return getJson<CourseListResponse>(`/public/courses/${suffix}`);
}

export async function getCourse(provider: string, slug: string): Promise<CourseDetail | null> {
  try {
    return await getJson<CourseDetail>(`/public/courses/${provider}/${slug}/`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) return null;
    throw error;
  }
}

export async function getShoppingPosts(options?: {
  limit?: number;
  q?: string;
  type?: ShoppingPostType;
}): Promise<ShoppingPostListResponse> {
  const params = new URLSearchParams();
  if (options?.limit) params.set("limit", String(options.limit));
  if (options?.q) params.set("q", options.q);
  if (options?.type) params.set("type", options.type);
  const suffix = params.size ? `?${params.toString()}` : "";
  return getJson<ShoppingPostListResponse>(`/public/shop/${suffix}`);
}

export async function getShoppingPost(slug: string): Promise<ShoppingPostDetail | null> {
  try {
    return await getJson<ShoppingPostDetail>(`/public/shop/${slug}/`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) return null;
    throw error;
  }
}

export async function getCourseSitemapEntries(): Promise<SitemapResponse> {
  return getJson<SitemapResponse>("/public/courses/sitemap/");
}

export async function getShoppingSitemapEntries(): Promise<SitemapResponse> {
  return getJson<SitemapResponse>("/public/shop/sitemap/");
}
