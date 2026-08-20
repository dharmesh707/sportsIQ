import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { AnalysisResult } from "@/api/types";
import { Card, SectionLabel } from "@/components/Primitives";
import { SportBadge } from "@/components/SportBadge";
import { ScoreRing } from "@/components/ScoreRing";
import { FaultCard } from "@/components/FaultCard";
import { PoseQualityBadge } from "@/components/PoseQualityBadge";
import { AthleteComparisonCard } from "@/components/AthleteComparisonCard";
import { FeatureComparisonTable } from "@/components/FeatureComparisonTable";
import { color, space, type } from "@/theme/tokens";
import { formatActionLabel, formatMetricKey } from "@/utils/format";

export function AnalysisResultView({ result }: { result: AnalysisResult }) {
  const metricEntries = Object.entries(result.metrics ?? {}).filter(
    ([, value]) => typeof value === "number"
  );
  const jointEntries = Object.entries(result.jointAngles ?? {});
  const hardFaults = result.faults.filter((f) => f.type === "hard");
  const softFaults = result.faults.filter((f) => f.type === "soft");
  const isSimulated = result.dataSource === "simulated";
  const reliable = result.poseQuality?.isReliable ?? true;

  return (
    <View style={{ gap: space.lg }}>
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <SportBadge sportType={result.sportType} />
          {isSimulated ? (
            <View style={styles.simulatedPill}>
              <Text style={styles.simulatedPillText}>PREVIEW DATA</Text>
            </View>
          ) : null}
        </View>
        <Text style={styles.actionLabel}>{formatActionLabel(result.actionLabel)}</Text>
      </View>

      {isSimulated ? (
        <View style={styles.simulatedBanner}>
          <Text style={styles.simulatedBannerText}>
            This sport isn't implemented yet. Everything below is placeholder data, not an
            analysis of your video.
          </Text>
        </View>
      ) : null}

      {result.poseQuality ? <PoseQualityBadge quality={result.poseQuality} /> : null}

      <Card style={styles.scoreCard}>
        <ScoreRing score={result.overallScore} sublabel="TECHNIQUE SCORE" />
        <Text style={styles.comparison}>{result.professionalComparison}</Text>
      </Card>

      {result.athleteComparison ? (
        <AthleteComparisonCard comparison={result.athleteComparison} />
      ) : null}

      {result.featureComparison && result.featureComparison.length > 0 ? (
        <FeatureComparisonTable features={result.featureComparison} reliable={reliable} />
      ) : null}

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

      {result.weaknesses && result.weaknesses.length > 0 && (
        <View>
          <SectionLabel>NEEDS WORK</SectionLabel>
          <Card>
            {result.weaknesses.map((w, i) => (
              <Text key={i} style={styles.listItemNegative}>
                {"\u25CF"}  {w}
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
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  actionLabel: { ...type.h2, color: color.ink },
  simulatedPill: {
    backgroundColor: color.softFaultBg,
    borderRadius: 999,
    paddingHorizontal: space.sm,
    paddingVertical: 3,
  },
  simulatedPillText: { fontSize: 10, letterSpacing: 0.8, color: color.softFault, fontWeight: "700" as const },
  simulatedBanner: {
    backgroundColor: color.softFaultBg,
    borderRadius: 14,
    padding: space.md,
  },
  simulatedBannerText: { ...type.small, color: color.ink },
  scoreCard: { alignItems: "center", paddingVertical: space.xl },
  comparison: { ...type.body, color: color.inkMuted, textAlign: "center", marginTop: space.sm },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: space.lg },
  statCell: { width: "42%", gap: 2 },
  statValue: { ...type.h2, color: color.ink },
  statLabel: { ...type.small, color: color.inkFaint },
  listItem: { ...type.body, color: color.inkMuted, marginBottom: space.xs },
  listItemPositive: { ...type.body, color: color.positive, marginBottom: space.xs },
  listItemNegative: { ...type.body, color: color.hardFault, marginBottom: space.xs },
});
