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
  SportsResponse,
  SportType,
  User,
  ANALYZE_TIMEOUT_MS,
  DEFAULT_TIMEOUT_MS,
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
  init: RequestInit & { skipAuth?: boolean; timeoutMs?: number } = {}
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

  // Every request gets a hard timeout so the UI can never be stuck on a
  // loading screen indefinitely - a dropped connection or a server that
  // hangs would otherwise spin the caller's loading state forever.
  const timeoutMs = init.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, { ...init, headers, signal: controller.signal });
  } catch (err) {
    const isAbort = err instanceof Error && err.name === "AbortError";
    if (isAbort) {
      throw new ApiError(
        0,
        "TIMEOUT",
        "The analysis is taking longer than expected. Please try again."
      );
    }
    throw new ApiError(0, "NETWORK_ERROR", "Unable to connect to the analysis server.");
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  let json: unknown;
  try {
    json = await res.json();
  } catch {
    // Backend sent something that isn't valid JSON at all - a malformed
    // response, not a contract-shaped error. Surface it distinctly so the
    // UI copy can say "unexpected response" instead of quoting a code that
    // was never actually returned.
    throw new ApiError(
      res.status,
      "MALFORMED_RESPONSE",
      "Received an unexpected response from the server."
    );
  }

  if (!res.ok) {
    // Contract guarantees { error: { code, message } } from every endpoint,
    // but a malformed 500 from an unrelated proxy/gateway could still slip
    // through with a different shape - fall back safely rather than reading
    // undefined.error.code and throwing a raw TypeError.
    const shape = json as Partial<ApiErrorShape>;
    const code = shape?.error?.code ?? "INTERNAL_ERROR";
    const message = shape?.error?.message ?? "Something went wrong. Please try again.";
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
    // Real CPU inference on a several-second clip can legitimately take
    // 30-90s, so this request gets a longer timeout than everything else.
    return request<AnalysisResult>("/analyze", {
      method: "POST",
      body: form,
      timeoutMs: ANALYZE_TIMEOUT_MS,
    });
  },

  // ---- Sport support status (v2 additive) ----
  sports: () => request<SportsResponse>("/sports"),

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
