import React, { useCallback, useEffect, useState } from "react";
import { Dimensions, Pressable, StyleSheet, Text, View } from "react-native";
import { VictoryChart, VictoryLine, VictoryAxis, VictoryScatter } from "victory-native";
import { api } from "@/api/client";
import { ApiError, ProgressRange, ProgressResponse, SportType } from "@/api/types";
import { Screen, Card, SectionLabel } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { color, radius, space, type } from "@/theme/tokens";
import { SPORT_OPTIONS, getSportMeta } from "@/utils/sportMeta";
import { formatDateShort, formatFaultCode, formatPercent } from "@/utils/format";

const RANGES: { value: ProgressRange; label: string }[] = [
  { value: "7d", label: "7D" },
  { value: "30d", label: "30D" },
  { value: "90d", label: "90D" },
  { value: "all", label: "ALL" },
];

const CHART_WIDTH = Dimensions.get("window").width - space.lg * 2 - space.lg * 2;

export default function ProgressScreen() {
  const [sportType, setSportType] = useState<SportType>("badminton");
  const [range, setRange] = useState<ProgressRange>("30d");
  const [data, setData] = useState<ProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.progress(sportType, range);
      setData(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load progress.");
    } finally {
      setLoading(false);
    }
  }, [sportType, range]);

  useEffect(() => {
    load();
  }, [load]);

  const meta = getSportMeta(sportType);
  const hasData = (data?.dataPoints.length ?? 0) > 0;

  return (
    <Screen>
      <Text style={styles.title}>Progress</Text>

      <View>
        <SectionLabel>SPORT</SectionLabel>
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

      <View style={styles.rangeRow}>
        {RANGES.map((r) => (
          <Pressable
            key={r.value}
            onPress={() => setRange(r.value)}
            style={[styles.rangeChip, range === r.value && { backgroundColor: meta.accent }]}
          >
            <Text style={[styles.rangeChipText, range === r.value && { color: color.bg }]}>
              {r.label}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading ? (
        <LoadingState label="Loading progress…" />
      ) : error ? (
        <ErrorBanner message={error} onRetry={load} />
      ) : !data || !hasData ? (
        <EmptyState
          title="No data for this sport yet"
          body="A sport you haven't tried is a valid empty state, not an error — analyze a clip to start a baseline."
        />
      ) : (
        <>
          <Card style={styles.baselineCard}>
            <View style={styles.baselineRow}>
              <View style={styles.baselineStat}>
                <Text style={styles.baselineValue}>{Math.round(data.baseline.initialScore)}</Text>
                <Text style={styles.baselineLabel}>BASELINE</Text>
              </View>
              <View style={styles.arrowWrap}>
                <Text style={[styles.arrow, { color: meta.accent }]}>→</Text>
                <Text
                  style={[
                    styles.percentChange,
                    { color: data.baseline.percentChange >= 0 ? color.positive : color.hardFault },
                  ]}
                >
                  {formatPercent(data.baseline.percentChange)}
                </Text>
              </View>
              <View style={styles.baselineStat}>
                <Text style={[styles.baselineValue, { color: meta.accent }]}>
                  {Math.round(data.baseline.currentScore)}
                </Text>
                <Text style={styles.baselineLabel}>CURRENT</Text>
              </View>
            </View>
            <Text style={styles.baselineNote}>
              Measured against your own {formatDateShort(data.baseline.establishedAt)} baseline —
              never against other players.
            </Text>
          </Card>

          <View>
            <SectionLabel>SCORE OVER TIME</SectionLabel>
            <Card>
              <VictoryChart width={CHART_WIDTH} height={200} padding={{ top: 16, bottom: 32, left: 40, right: 16 }}>
                <VictoryAxis
                  tickFormat={(t: number) => formatDateShort(data.dataPoints[t]?.date ?? "")}
                  style={{
                    axis: { stroke: color.line },
                    tickLabels: { fill: color.inkFaint, fontSize: 9 },
                    grid: { stroke: "transparent" },
                  }}
                />
                <VictoryAxis
                  dependentAxis
                  style={{
                    axis: { stroke: color.line },
                    tickLabels: { fill: color.inkFaint, fontSize: 9 },
                    grid: { stroke: color.line, strokeDasharray: "2,4" },
                  }}
                />
                <VictoryLine
                  data={data.dataPoints.map((d, i) => ({ x: i, y: d.score }))}
                  style={{ data: { stroke: meta.accent, strokeWidth: 2.5 } }}
                />
                <VictoryScatter
                  data={data.dataPoints.map((d, i) => ({ x: i, y: d.score }))}
                  size={4}
                  style={{ data: { fill: meta.accent } }}
                />
              </VictoryChart>
            </Card>
          </View>

          {data.faultTrends.length > 0 && (
            <View>
              <SectionLabel>FAULT TRENDS</SectionLabel>
              <View style={{ gap: space.sm }}>
                {data.faultTrends.map((ft, i) => {
                  const total = ft.occurrences.reduce((s, o) => s + o.count, 0);
                  const accentColor = ft.faultType === "hard" ? color.hardFault : color.softFault;
                  return (
                    <Card key={i} style={styles.faultTrendRow}>
                      <View style={[styles.faultTrendDot, { backgroundColor: accentColor }]} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.faultTrendCode}>{formatFaultCode(ft.faultCode)}</Text>
                        <Text style={styles.faultTrendMeta}>
                          {total} occurrence{total === 1 ? "" : "s"} over this range
                        </Text>
                      </View>
                    </Card>
                  );
                })}
              </View>
            </View>
          )}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...type.h1, color: color.ink },
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
  rangeRow: { flexDirection: "row", gap: space.xs, backgroundColor: color.bgElevated2, borderRadius: radius.pill, padding: 4, alignSelf: "flex-start" },
  rangeChip: { paddingVertical: 6, paddingHorizontal: space.md, borderRadius: radius.pill },
  rangeChipText: { ...type.smallMedium, color: color.inkMuted },
  baselineCard: { gap: space.md },
  baselineRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  baselineStat: { alignItems: "center", gap: 2 },
  baselineValue: { ...type.h1, color: color.ink },
  baselineLabel: { ...type.label, color: color.inkFaint },
  arrowWrap: { alignItems: "center", gap: 2 },
  arrow: { fontSize: 22 },
  percentChange: { ...type.smallMedium },
  baselineNote: { ...type.small, color: color.inkFaint, textAlign: "center" },
  faultTrendRow: { flexDirection: "row", alignItems: "center", gap: space.sm },
  faultTrendDot: { width: 8, height: 8, borderRadius: 4 },
  faultTrendCode: { ...type.bodyMedium, color: color.ink },
  faultTrendMeta: { ...type.small, color: color.inkFaint },
});
