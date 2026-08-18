import {
  ApiError,
  ApiErrorShape,
  AuthResponse,
  AnalysisResult,
  HistoryResponse,
  DashboardResponse,
  ProgressResponse,
  ProgressRange,
  HealthSummary,
  HealthSyncPayload,
  NutritionPlanResponse,
  SportType,
  User,
} from "./types";

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type TokenGetter = () => string | null;
type UnauthorizedHandler = () => void;

// Wired up once by AuthContext at app start — this is the single
// interceptor/handler for 401s the build brief asks for (non-negotiable #5),
// rather than per-screen logic scattered around.
let getToken: TokenGetter = () => null;
let onUnauthorized: UnauthorizedHandler = () => {};

export function configureApiClient(opts: {
  getToken: TokenGetter;
  onUnauthorized: UnauthorizedHandler;
}) {
  getToken = opts.getToken;
  onUnauthorized = opts.onUnauthorized;
}

async function request<T>(
  path: string,
  init: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };

  const isFormData =
    typeof FormData !== "undefined" && init.body instanceof FormData;
  if (!isFormData && init.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  if (!init.skipAuth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  } catch (networkErr) {
    throw new ApiError(0, "NETWORK_ERROR", "Couldn't reach the server. Check your connection.");
  }

  if (res.status === 204) {
    return undefined as T;
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    throw new ApiError(res.status, "INTERNAL_ERROR", "Unexpected response from server.");
  }

  if (!res.ok) {
    // Contract guarantees this exact shape from every endpoint.
    const shape = json as Partial<ApiErrorShape>;
    const code = shape?.error?.code ?? "INTERNAL_ERROR";
    const message = shape?.error?.message ?? "Something went wrong.";
    if (res.status === 401) {
      onUnauthorized();
    }
    throw new ApiError(res.status, code, message);
  }

  return json as T;
}

export const api = {
  // ---- Auth (Section 1) ----
  register: (email: string, password: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    }),

  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    }),

  me: () => request<{ user: User }>("/auth/me"),

  // ---- Core analysis (Section 2) ----
  analyze: (video: { uri: string; name: string; type: string }, sportType: SportType) => {
    const form = new FormData();
    // React Native FormData file shape.
    form.append("video", {
      uri: video.uri,
      name: video.name,
      type: video.type,
    } as unknown as Blob);
    form.append("sportType", sportType);
    return request<AnalysisResult>("/analyze", { method: "POST", body: form });
  },

  history: (params: { page?: number; pageSize?: number; sportType?: SportType } = {}) => {
    const q = new URLSearchParams();
    if (params.page) q.set("page", String(params.page));
    if (params.pageSize) q.set("pageSize", String(params.pageSize));
    if (params.sportType) q.set("sportType", params.sportType);
    const qs = q.toString();
    return request<HistoryResponse>(`/history${qs ? `?${qs}` : ""}`);
  },

  analysisById: (analysisId: string) =>
    request<AnalysisResult>(`/analyze/${encodeURIComponent(analysisId)}`),

  // ---- Dashboard & progress (Section 3) ----
  dashboard: () => request<DashboardResponse>("/dashboard"),

  progress: (sportType: SportType, range: ProgressRange = "30d") =>
    request<ProgressResponse>(
      `/progress?sportType=${encodeURIComponent(sportType)}&range=${range}`
    ),

  // ---- Health / wearable (Section 4, optional enrichment) ----
  syncHealthData: (payload: HealthSyncPayload) =>
    request<{ ok: true }>("/health-data/sync", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  healthSummary: () => request<HealthSummary>("/health-data/summary"),

  // ---- Nutrition (Section 5, optional enrichment) ----
  nutritionPlan: (sportType: SportType) =>
    request<NutritionPlanResponse>(
      `/nutrition/plan?sportType=${encodeURIComponent(sportType)}`
    ),
};
