/**
 * Health Connect wrapper (Android on-device Health Connect API — NOT the
 * deprecated Google Fit API). Requires an Expo dev build; this module will
 * throw/no-op under Expo Go, which is why every call site treats it as
 * optional enrichment and never blocks core screens on it (per brief Section
 * 5 and build-prompt Section on Train screen).
 */
import { Platform } from "react-native";
import { HealthSyncPayload } from "@/api/types";

let HealthConnectClient: typeof import("react-native-health-connect") | null = null;
try {
  // Lazily required so iOS / Expo Go builds don't crash on import.
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  HealthConnectClient = require("react-native-health-connect");
} catch {
  HealthConnectClient = null;
}

export interface HealthConnectAvailability {
  supported: boolean;
  reason?: string;
}

export function checkAvailability(): HealthConnectAvailability {
  if (Platform.OS !== "android") {
    return { supported: false, reason: "Health Connect is Android-only." };
  }
  if (!HealthConnectClient) {
    return {
      supported: false,
      reason: "Requires an Expo dev build (not available in Expo Go).",
    };
  }
  return { supported: true };
}

export async function requestPermissionsAndRead(): Promise<HealthSyncPayload | null> {
  const availability = checkAvailability();
  if (!availability.supported || !HealthConnectClient) return null;

  const initialized = await HealthConnectClient.initialize();
  if (!initialized) return null;

  await HealthConnectClient.requestPermission([
    { accessType: "read", recordType: "Steps" },
    { accessType: "read", recordType: "HeartRate" },
    { accessType: "read", recordType: "ActiveCaloriesBurned" },
    { accessType: "read", recordType: "ExerciseSession" },
  ]);

  const now = new Date();
  const startOfDay = new Date(now);
  startOfDay.setHours(0, 0, 0, 0);
  const timeRangeFilter = {
    operator: "between" as const,
    startTime: startOfDay.toISOString(),
    endTime: now.toISOString(),
  };

  const stepsRecords = await HealthConnectClient.readRecords("Steps", { timeRangeFilter });
  const heartRateRecords = await HealthConnectClient.readRecords("HeartRate", { timeRangeFilter });
  const exerciseRecords = await HealthConnectClient.readRecords("ExerciseSession", {
    timeRangeFilter,
  });

  const steps = (stepsRecords.records ?? []).reduce(
    (sum: number, r: { count?: number }) => sum + (r.count ?? 0),
    0
  );

  const allBpm: number[] = [];
  for (const r of heartRateRecords.records ?? []) {
    for (const sample of r.samples ?? []) {
      if (typeof sample.beatsPerMinute === "number") allBpm.push(sample.beatsPerMinute);
    }
  }
  const heartRateAvg = allBpm.length
    ? Math.round(allBpm.reduce((a: number, b: number) => a + b, 0) / allBpm.length)
    : 0;

  const activeMinutes = (exerciseRecords.records ?? []).reduce(
    (sum: number, r: { startTime: string; endTime: string }) => {
      const durationMin = (new Date(r.endTime).getTime() - new Date(r.startTime).getTime()) / 60000;
      return sum + Math.max(0, durationMin);
    },
    0
  );

  return {
    steps,
    heartRateAvg,
    activeMinutes: Math.round(activeMinutes),
    syncedAt: now.toISOString(),
  };
}
