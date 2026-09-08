const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api";

export type HealthResponse = {
  status: string;
  database: string;
};

export type ProviderSummary = {
  slug: string;
  name: string;
};

export type CoursePrice = {
  amount: string | null;
  currency: string;
  is_free: boolean;
  price_type: string;
  observed_at: string;
};

export type CourseSummary = {
  id: number;
  provider: ProviderSummary;
  title: string;
  slug: string;
  url: string;
  outbound_url: string;
  outbound_is_affiliate: boolean;
  thumbnail_url: string;
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
  first_seen_at: string;
  last_seen_at: string;
  eligibility: {
    score: number;
    evaluated_at: string;
  };
};

export type CourseListResponse = {
  generated_at: string;
  count: number;
  results: CourseSummary[];
};

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });

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

  if (options?.limit) {
    params.set("limit", String(options.limit));
  }

  if (options?.q) {
    params.set("q", options.q);
  }

  const suffix = params.size ? `?${params.toString()}` : "";
  return getJson<CourseListResponse>(`/public/courses/${suffix}`);
}

export async function getCourse(
  provider: string,
  slug: string,
): Promise<CourseDetail | null> {
  try {
    return await getJson<CourseDetail>(`/public/courses/${provider}/${slug}/`);
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) {
      return null;
    }
    throw error;
  }
}
