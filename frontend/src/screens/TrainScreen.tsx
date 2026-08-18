import React, { useCallback, useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { api } from "@/api/client";
import { ApiError, HealthSummary, NutritionPlanResponse, SportType } from "@/api/types";
import { Screen, Card, PrimaryButton, SectionLabel } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { LoadingState } from "@/components/LoadingState";
import { color, radius, space, type } from "@/theme/tokens";
import { SPORT_OPTIONS } from "@/utils/sportMeta";
import { formatDateTime, snakeToTitleCase } from "@/utils/format";
import { checkAvailability, requestPermissionsAndRead } from "@/health/healthConnect";

export default function TrainScreen() {
  const [sportType, setSportType] = useState<SportType>("badminton");

  return (
    <Screen>
      <Text style={styles.title}>Train</Text>
      <Text style={styles.subtitle}>
        Optional enrichment — the rest of SportsIQ works fully without either of these.
      </Text>

      <HealthConnectCard />

      <View>
        <SectionLabel>NUTRITION PLAN</SectionLabel>
        <View style={styles.chipRow}>
          {SPORT_OPTIONS.map((opt) => (
            <Pressable
              key={opt.value}
              onPress={() => setSportType(opt.value)}
              style={[styles.chip, sportType === opt.value && styles.chipActive]}
            >
              <Text style={[styles.chipText, sportType === opt.value && styles.chipTextActive]}>
                {opt.label}
              </Text>
            </Pressable>
          ))}
        </View>
      </View>
      <NutritionCard sportType={sportType} />
    </Screen>
  );
}

function HealthConnectCard() {
  const [summary, setSummary] = useState<HealthSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const availability = checkAvailability();

  const loadSummary = useCallback(async () => {
    setError(null);
    try {
      const res = await api.healthSummary();
      setSummary(res);
    } catch (e) {
      // Optional enrichment — never blocks the screen, just shows inline.
      setError(e instanceof ApiError ? e.message : "Couldn't load health data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const onSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const reading = await requestPermissionsAndRead();
      if (reading) {
        await api.syncHealthData(reading);
        await loadSummary();
      } else {
        setError(availability.reason ?? "Health Connect isn't available on this device.");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't sync Health Connect data.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <View>
      <SectionLabel>HEALTH CONNECT</SectionLabel>
      <Card style={{ gap: space.md }}>
        {loading ? (
          <LoadingState label="Checking sync status…" />
        ) : (
          <>
            <View style={styles.healthGrid}>
              <HealthStat label="Steps" value={summary ? String(summary.steps) : "0"} />
              <HealthStat label="Avg HR" value={summary?.heartRateAvg ? `${summary.heartRateAvg} bpm` : "—"} />
              <HealthStat label="Active" value={summary ? `${summary.activeMinutes}m` : "0m"} />
            </View>
            <Text style={styles.syncMeta}>
              {summary?.lastSyncedAt
                ? `Last synced ${formatDateTime(summary.lastSyncedAt)}`
                : "Never synced"}
            </Text>
            {!availability.supported ? (
              <Text style={styles.unavailable}>{availability.reason}</Text>
            ) : null}
            {error ? <ErrorBanner message={error} /> : null}
            <PrimaryButton
              label={syncing ? "Syncing…" : "Sync now"}
              onPress={onSync}
              loading={syncing}
              disabled={!availability.supported}
            />
          </>
        )}
      </Card>
    </View>
  );
}

function HealthStat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.healthStat}>
      <Text style={styles.healthValue}>{value}</Text>
      <Text style={styles.healthLabel}>{label}</Text>
    </View>
  );
}

function NutritionCard({ sportType }: { sportType: SportType }) {
  const [plan, setPlan] = useState<NutritionPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.nutritionPlan(sportType);
      setPlan(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load a nutrition plan.");
    } finally {
      setLoading(false);
    }
  }, [sportType]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingState label="Loading plan…" />;
  if (error) return <ErrorBanner message={error} onRetry={load} />;
  if (!plan) return null;

  return (
    <View style={{ gap: space.md }}>
      <Card style={{ gap: space.sm }}>
        <Text style={styles.energyCategory}>{snakeToTitleCase(plan.energySystemCategory)}</Text>
        <View style={styles.macroRow}>
          <MacroStat label="Protein" value={`${plan.macroGuidance.proteinG}g`} />
          <MacroStat label="Carbs" value={`${plan.macroGuidance.carbsG}g`} />
          <MacroStat label="Fat" value={`${plan.macroGuidance.fatG}g`} />
        </View>
      </Card>

      {plan.foodSuggestions.length > 0 && (
        <Card>
          <Text style={styles.cardHeading}>Food suggestions</Text>
          {plan.foodSuggestions.map((f, i) => (
            <Text key={i} style={styles.listItem}>
              {"\u25CF"}  {f.item} <Text style={styles.region}>· {f.region}</Text>
            </Text>
          ))}
        </Card>
      )}

      {plan.exercises.length > 0 && (
        <Card>
          <Text style={styles.cardHeading}>Exercises</Text>
          {plan.exercises.map((ex, i) => (
            <View key={i} style={{ marginBottom: space.sm }}>
              <Text style={styles.exerciseName}>{ex.name}</Text>
              <Text style={styles.exerciseRationale}>{ex.rationale}</Text>
            </View>
          ))}
        </Card>
      )}

      <Text style={styles.disclaimer}>{plan.disclaimer}</Text>
    </View>
  );
}

function MacroStat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.macroStat}>
      <Text style={styles.macroValue}>{value}</Text>
      <Text style={styles.macroLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  title: { ...type.h1, color: color.ink },
  subtitle: { ...type.small, color: color.inkFaint, marginTop: -space.sm },
  chipRow: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  chip: {
    borderWidth: 1,
    borderColor: color.line,
    borderRadius: radius.pill,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
  },
  chipActive: { backgroundColor: color.accent, borderColor: color.accent },
  chipText: { ...type.smallMedium, color: color.inkMuted },
  chipTextActive: { color: color.accentInk },
  healthGrid: { flexDirection: "row", justifyContent: "space-between" },
  healthStat: { alignItems: "center", gap: 2 },
  healthValue: { ...type.h2, color: color.ink },
  healthLabel: { ...type.small, color: color.inkFaint },
  syncMeta: { ...type.small, color: color.inkFaint, textAlign: "center" },
  unavailable: { ...type.small, color: color.softFault, textAlign: "center" },
  energyCategory: { ...type.h3, color: color.accent },
  macroRow: { flexDirection: "row", justifyContent: "space-between" },
  macroStat: { alignItems: "center", gap: 2 },
  macroValue: { ...type.h3, color: color.ink },
  macroLabel: { ...type.small, color: color.inkFaint },
  cardHeading: { ...type.label, color: color.inkFaint, marginBottom: space.xs },
  listItem: { ...type.body, color: color.inkMuted, marginBottom: space.xs },
  region: { color: color.inkFaint },
  exerciseName: { ...type.bodyMedium, color: color.ink },
  exerciseRationale: { ...type.small, color: color.inkMuted },
  disclaimer: { ...type.small, color: color.inkFaint, textAlign: "center", fontStyle: "italic" },
});
