/**
 * Every type here mirrors ../../API_CONTRACT.md field-for-field, in
 * camelCase (the backend serializes camelCase — see backend's
 * app/schemas/base.py). If a field name here doesn't match the contract,
 * the contract is right, fix this file.
 */

import { SportType } from '../constants/sports';

export interface User {
  id: string;
  email: string;
  createdAt: string; // ISO8601
}

export interface AuthResponse {
  accessToken: string;
  user: User;
}

export type FaultType = 'hard' | 'soft';

export interface Fault {
  type: FaultType;
  description: string;
  frame: number;
}

export interface AnalysisResult {
  analysisId: string;
  sportType: SportType;
  actionLabel: string;
  overallScore: number;
  professionalComparison: string;
  metrics: Record<string, unknown>; // sport-specific, see contract
  jointAngles: Record<string, number>;
  faults: Fault[];
  strengths: string[];
  recommendations: string[];
  createdAt: string; // ISO8601
}

export interface AnalysisResultSummary {
  analysisId: string;
  sportType: SportType;
  actionLabel: string;
  overallScore: number;
  createdAt: string;
}

export interface HistoryResponse {
  analyses: AnalysisResultSummary[];
}

export interface MacroGuidance {
  proteinG: number;
  carbsG: number;
  fatG: number;
}

export interface FoodSuggestion {
  item: string;
  region: string;
}

export interface Exercise {
  name: string;
  rationale: string;
}

export interface NutritionPlan {
  sportType: SportType;
  energySystemCategory: string;
  macroGuidance: MacroGuidance;
  foodSuggestions: FoodSuggestion[];
  exercises: Exercise[];
  disclaimer: string;
}

export interface HealthDataSummary {
  steps: number;
  heartRateAvg: number;
  activeMinutes: number;
  lastSyncedAt: string | null;
}

/**
 * Contract rule #3: every error response has this exact shape. See
 * src/api/client.ts — the axios interceptor normalizes thrown errors to
 * this type, so screens/hooks can always assume ApiError, never a raw
 * axios error.
 */
export interface ApiError {
  code: string;
  message: string;
}

/**
 * DASHBOARD/PROGRESS WARNING: the backend's own README flags these two as
 * placeholder shapes — contract says "unchanged from v1.0" but the real
 * v1.0 shape wasn't available when the backend was scaffolded. Don't build
 * heavily against DashboardResponse/ProgressResponse below until Dharmesh
 * confirms they match the real v1.0 backend code.
 */
export interface RecentAnalysisItem {
  analysisId: string;
  sportType: SportType;
  actionLabel: string;
  overallScore: number;
  createdAt: string;
}

export interface DashboardResponse {
  totalAnalyses: number;
  averageScore: number;
  currentStreakDays: number;
  recentAnalyses: RecentAnalysisItem[];
}

export interface ProgressPoint {
  date: string;
  overallScore: number;
}

export interface ProgressResponse {
  sportType: SportType;
  points: ProgressPoint[];
}
