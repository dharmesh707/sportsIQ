import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { AnalysisResult } from "@/api/types";
import { Card, SectionLabel } from "@/components/Primitives";
import { SportBadge } from "@/components/SportBadge";
import { ScoreRing } from "@/components/ScoreRing";
import { FaultCard } from "@/components/FaultCard";
import { color, space, type } from "@/theme/tokens";
import { formatActionLabel, formatMetricKey } from "@/utils/format";

export function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const metricEntries = Object.entries(result.metrics ?? {});
  const jointEntries = Object.entries(result.jointAngles ?? {});
  const hardFaults = result.faults.filter((f) => f.type === "hard");
  const softFaults = result.faults.filter((f) => f.type === "soft");

  return (
    <View style={{ gap: space.lg }}>
      <View style={styles.header}>
        <SportBadge sportType={result.sportType} />
        <Text style={styles.actionLabel}>{formatActionLabel(result.actionLabel)}</Text>
      </View>

      <Card style={styles.scoreCard}>
        <ScoreRing score={result.overallScore} sublabel="OVERALL" />
        <Text style={styles.comparison}>{result.professionalComparison}</Text>
      </Card>

      {(metricEntries.length > 0 || jointEntries.length > 0) && (
        <View>
          <SectionLabel>METRICS</SectionLabel>
          <Card style={styles.statGrid}>
            {[...metricEntries, ...jointEntries].map(([key, value]) => (
              <View key={key} style={styles.statCell}>
                <Text style={styles.statValue}>
                  {typeof value === "number" ? value.toFixed(1) : String(value)}
                </Text>
                <Text style={styles.statLabel}>{formatMetricKey(key)}</Text>
              </View>
            ))}
          </Card>
        </View>
      )}

      {result.strengths.length > 0 && (
        <View>
          <SectionLabel>STRENGTHS</SectionLabel>
          <Card>
            {result.strengths.map((s, i) => (
              <Text key={i} style={styles.listItemPositive}>
                {"\u25CF"}  {s}
              </Text>
            ))}
          </Card>
        </View>
      )}

      {hardFaults.length > 0 && (
        <View>
          <SectionLabel>HARD FAULTS ({hardFaults.length})</SectionLabel>
          <View style={{ gap: space.sm }}>
            {hardFaults.map((f, i) => (
              <FaultCard key={i} fault={f} />
            ))}
          </View>
        </View>
      )}

      {softFaults.length > 0 && (
        <View>
          <SectionLabel>STYLE NOTES ({softFaults.length})</SectionLabel>
          <View style={{ gap: space.sm }}>
            {softFaults.map((f, i) => (
              <FaultCard key={i} fault={f} />
            ))}
          </View>
        </View>
      )}

      {result.recommendations.length > 0 && (
        <View>
          <SectionLabel>RECOMMENDATIONS</SectionLabel>
          <Card>
            {result.recommendations.map((r, i) => (
              <Text key={i} style={styles.listItem}>
                {i + 1}. {r}
              </Text>
            ))}
          </Card>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: space.sm },
  actionLabel: { ...type.h2, color: color.ink },
  scoreCard: { alignItems: "center", paddingVertical: space.xl },
  comparison: { ...type.body, color: color.inkMuted, textAlign: "center", marginTop: space.sm },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: space.lg },
  statCell: { width: "42%", gap: 2 },
  statValue: { ...type.h2, color: color.ink },
  statLabel: { ...type.small, color: color.inkFaint },
  listItem: { ...type.body, color: color.inkMuted, marginBottom: space.xs },
  listItemPositive: { ...type.body, color: color.positive, marginBottom: space.xs },
});
