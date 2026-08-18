/**
 * Types mirror API_CONTRACT_final.md field-for-field. If this file and the
 * contract ever disagree, the contract is right — fix this file.
 *
 * sportType is a CLOSED enum (contract Section "Global rules" #2) — never add
 * a sixth value here without the contract changing first.
 */

export type SportType =
  | "badminton"
  | "tennis"
  | "table_tennis"
  | "cricket_bowling"
  | "archery";

export const SPORT_TYPES: SportType[] = [
  "badminton",
  "tennis",
  "table_tennis",
  "cricket_bowling",
  "archery",
];

// Section 8 — closed, extend-only with team sign-off.
export type ErrorCode =
  | "UNAUTHORIZED"
  | "INVALID_CREDENTIALS"
  | "EMAIL_ALREADY_REGISTERED"
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "UNSUPPORTED_SPORT_TYPE"
  | "VIDEO_PROCESSING_FAILED"
  | "INTERNAL_ERROR"
  | string; // extend-only: unrecognized codes must not crash the client

// Section "every error response" shape.
export interface ApiErrorShape {
  error: {
    code: ErrorCode;
    message: string;
  };
}

export class ApiError extends Error {
  code: ErrorCode;
  status: number;
  constructor(status: number, code: ErrorCode, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

// ---- Section 1: Auth ----

export interface User {
  id: string;
  email: string;
  createdAt: string;
}

export interface AuthResponse {
  accessToken: string;
  user: User;
}

// ---- Section 2: Core analysis ----

export type FaultType = "hard" | "soft";

// Section 2.1 — extend-only per sport. Unrecognized values are rendered via
// formatActionLabel() as a fallback, never crash.
export type ActionLabel = string;

// Section 2.2 — extend-only per sport. Same fallback rule.
export type FaultCode = string;

export interface Fault {
  faultCode: FaultCode;
  type: FaultType;
  description: string;
  frame: number;
  referenceSource: string | null;
}

// Open key-value maps of numeric stats (Section 2.3).
export type MetricMap = Record<string, number>;
export type JointAngleMap = Record<string, number>;

export interface AnalysisResult {
  analysisId: string;
  sportType: SportType;
  actionLabel: ActionLabel;
  overallScore: number;
  professionalComparison: string;
  metrics: MetricMap;
  jointAngles: JointAngleMap;
  faults: Fault[];
  strengths: string[];
  recommendations: string[];
  createdAt: string;
}

export interface AnalysisResultSummary {
  analysisId: string;
  sportType: SportType;
  actionLabel: ActionLabel;
  overallScore: number;
  hardFaultCount: number;
  softFaultCount: number;
  createdAt: string;
}

export interface Pagination {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface HistoryResponse {
  analyses: AnalysisResultSummary[];
  pagination: Pagination;
}

// ---- Section 3: Dashboard & progress ----

export type Trend = "improving" | "stable" | "declining" | "insufficient_data";

export interface DashboardSummary {
  totalSessions: number;
  sportsPracticed: SportType[];
  currentStreakDays: number;
  lastSessionAt: string | null;
}

export interface SportBreakdownEntry {
  sportType: SportType;
  sessionCount: number;
  averageScore: number;
  lastSessionAt: string | null;
  trend: Trend;
}

export interface RecentSession {
  sessionId: string;
  sportType: SportType;
  score: number;
  hardFaultCount: number;
  softFaultCount: number;
  createdAt: string;
}

export interface TopFault {
  faultCode: FaultCode;
  sportType: SportType;
  faultType: FaultType;
  occurrenceCount: number;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  sportBreakdown: SportBreakdownEntry[];
  recentSessions: RecentSession[]; // capped at 5 by backend
  topFaults: TopFault[]; // capped at 5 by backend
  recommendations: string[];
}

export type ProgressRange = "7d" | "30d" | "90d" | "all";

export interface ProgressDataPoint {
  date: string;
  sessionId: string;
  score: number;
  hardFaultCount: number;
  softFaultCount: number;
}

export interface FaultTrendOccurrence {
  date: string;
  count: number;
}

export interface FaultTrend {
  faultCode: FaultCode;
  faultType: FaultType;
  occurrences: FaultTrendOccurrence[];
}

export interface ProgressResponse {
  sportType: SportType;
  range: { start: string; end: string };
  baseline: {
    initialScore: number;
    currentScore: number;
    percentChange: number;
    establishedAt: string;
  };
  dataPoints: ProgressDataPoint[];
  faultTrends: FaultTrend[];
}

// ---- Section 4: Health / wearable data ----

export interface HealthSyncPayload {
  steps: number;
  heartRateAvg: number;
  activeMinutes: number;
  syncedAt: string;
}

export interface HealthSummary {
  steps: number;
  heartRateAvg: number;
  activeMinutes: number;
  lastSyncedAt: string | null;
}

// ---- Section 5: Nutrition & fitness ----

// extend-only, current known values.
export type EnergySystemCategory =
  | "explosive_anaerobic"
  | "aerobic_endurance"
  | "mixed_intermittent"
  | "precision_static"
  | string;

export interface MacroGuidance {
  proteinG: number;
  carbsG: number;
  fatG: number;
}

export interface FoodSuggestion {
  item: string;
  region: string;
}

export interface ExerciseSuggestion {
  name: string;
  rationale: string;
}

export interface NutritionPlanResponse {
  sportType: SportType;
  energySystemCategory: EnergySystemCategory;
  macroGuidance: MacroGuidance;
  foodSuggestions: FoodSuggestion[];
  exercises: ExerciseSuggestion[];
  disclaimer: string;
}
