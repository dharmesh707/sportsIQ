import React, { useCallback, useEffect, useState } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import { api } from "@/api/client";
import { ApiError, DashboardResponse } from "@/api/types";
import { Screen, Card, SectionLabel } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { SportBadge } from "@/components/SportBadge";
import { TrendPill } from "@/components/TrendPill";
import { color, space, type } from "@/theme/tokens";
import { formatActionLabel, formatFaultCode, formatRelativeDay } from "@/utils/format";

export default function DashboardScreen() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await api.dashboard();
      setData(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load your dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Refresh whenever the tab regains focus (e.g. after a new analysis).
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  if (loading) {
    return (
      <Screen>
        <LoadingState label="Loading dashboard…" />
      </Screen>
    );
  }

  if (error) {
    return (
      <Screen>
        <ErrorBanner message={error} onRetry={load} />
      </Screen>
    );
  }

  if (!data) return null;

  const hasAnySessions = data.summary.totalSessions > 0;

  return (
    <Screen>
      <Text style={styles.title}>Dashboard</Text>

      {!hasAnySessions ? (
        <EmptyState
          title="Nothing tracked yet"
          body="Analyze your first clip and this becomes your training home base."
        />
      ) : (
        <>
          <Card style={styles.summaryCard}>
            <View style={styles.summaryRow}>
              <SummaryStat label="Sessions" value={String(data.summary.totalSessions)} />
              <SummaryStat label="Streak" value={`${data.summary.currentStreakDays}d`} />
              <SummaryStat label="Sports" value={String(data.summary.sportsPracticed.length)} />
            </View>
            <Text style={styles.lastSession}>
              Last session: {formatRelativeDay(data.summary.lastSessionAt)}
            </Text>
          </Card>

          {data.sportBreakdown.length > 0 && (
            <View>
              <SectionLabel>BY SPORT</SectionLabel>
              <View style={{ gap: space.sm }}>
                {data.sportBreakdown.map((s) => (
                  <Card key={s.sportType} style={styles.breakdownRow}>
                    <View style={{ gap: 6, flex: 1 }}>
                      <SportBadge sportType={s.sportType} />
                      <Text style={styles.breakdownMeta}>
                        {s.sessionCount} sessions · avg {Math.round(s.averageScore)}
                      </Text>
                    </View>
                    <TrendPill trend={s.trend} />
                  </Card>
                ))}
              </View>
            </View>
          )}

          {data.recentSessions.length > 0 && (
            <View>
              <SectionLabel>RECENT SESSIONS</SectionLabel>
              <View style={{ gap: space.sm }}>
                {data.recentSessions.map((s) => (
                  <Card
                    key={s.sessionId}
                    style={styles.sessionRow}
                  >
                    <SportBadge sportType={s.sportType} />
                    <Text style={styles.sessionScore}>{Math.round(s.score)}</Text>
                    <Text style={styles.sessionFaults}>
                      {s.hardFaultCount}H · {s.softFaultCount}S
                    </Text>
                  </Card>
                ))}
              </View>
            </View>
          )}

          {data.topFaults.length > 0 && (
            <View>
              <SectionLabel>TOP FAULTS</SectionLabel>
              <Card>
                {data.topFaults.map((f, i) => (
                  <View key={i} style={styles.faultRow}>
                    <View style={[styles.faultDot, { backgroundColor: f.faultType === "hard" ? color.hardFault : color.softFault }]} />
                    <Text style={styles.faultText}>{formatFaultCode(f.faultCode)}</Text>
                    <Text style={styles.faultCount}>×{f.occurrenceCount}</Text>
                  </View>
                ))}
              </Card>
            </View>
          )}

          {data.recommendations.length > 0 && (
            <View>
              <SectionLabel>COACH NOTES</SectionLabel>
              <Card>
                {data.recommendations.map((r, i) => (
                  <Text key={i} style={styles.recommendation}>
                    {i + 1}. {r}
                  </Text>
                ))}
              </Card>
            </View>
          )}
        </>
      )}
    </Screen>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryStat}>
      <Text style={styles.summaryValue}>{value}</Text>
      <Text style={styles.summaryLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  title: { ...type.h1, color: color.ink },
  summaryCard: { gap: space.md },
  summaryRow: { flexDirection: "row", justifyContent: "space-between" },
  summaryStat: { alignItems: "center", gap: 2 },
  summaryValue: { ...type.h1, color: color.accent },
  summaryLabel: { ...type.small, color: color.inkMuted },
  lastSession: { ...type.small, color: color.inkFaint, textAlign: "center" },
  breakdownRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  breakdownMeta: { ...type.small, color: color.inkMuted },
  sessionRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  sessionScore: { ...type.h3, color: color.ink },
  sessionFaults: { ...type.small, color: color.inkMuted },
  faultRow: { flexDirection: "row", alignItems: "center", gap: space.sm, paddingVertical: 4 },
  faultDot: { width: 8, height: 8, borderRadius: 4 },
  faultText: { ...type.body, color: color.ink, flex: 1 },
  faultCount: { ...type.smallMedium, color: color.inkFaint },
  recommendation: { ...type.body, color: color.inkMuted, marginBottom: space.xs },
});
