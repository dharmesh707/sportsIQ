import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { FeatureComparisonItem, FeatureVerdict } from "@/api/types";
import { Card, SectionLabel } from "@/components/Primitives";
import { color, radius, space, type } from "@/theme/tokens";

const VERDICT_COLOR: Record<FeatureVerdict, string> = {
  GOOD: color.positive,
  SLIGHT_DIFFERENCE: color.softFault,
  NEEDS_IMPROVEMENT: color.hardFault,
};

const VERDICT_LABEL: Record<FeatureVerdict, string> = {
  GOOD: "Good",
  SLIGHT_DIFFERENCE: "Slight difference",
  NEEDS_IMPROVEMENT: "Needs work",
};

function unitSuffix(unit: string): string {
  return unit === "deg" ? "\u00b0" : ` ${unit}`;
}

export function FeatureComparisonTable({
  features,
  reliable,
}: {
  features: FeatureComparisonItem[];
  reliable: boolean;
}) {
  if (features.length === 0) return null;
  return (
    <View>
      <SectionLabel>FEATURE COMPARISON</SectionLabel>
      <Card style={{ gap: 0, padding: 0 }}>
        <View style={styles.headerRow}>
          <Text style={[styles.headerCell, styles.featureCol]}>FEATURE</Text>
          <Text style={[styles.headerCell, styles.valueCol]}>YOU</Text>
          <Text style={[styles.headerCell, styles.valueCol]}>REFERENCE</Text>
          <Text style={[styles.headerCell, styles.verdictCol]}>VERDICT</Text>
        </View>
        {features.map((feature, index) => (
          <View
            key={feature.key}
            style={[styles.row, index === features.length - 1 && styles.lastRow]}
          >
            <Text style={[styles.cell, styles.featureCol, styles.featureLabel]}>
              {feature.label}
            </Text>
            <Text style={[styles.cell, styles.valueCol]}>
              {feature.userValue.toFixed(0)}
              {unitSuffix(feature.unit)}
            </Text>
            <Text style={[styles.cell, styles.valueCol, styles.referenceValue]}>
              {feature.referenceValue.toFixed(0)}
              {unitSuffix(feature.unit)}
            </Text>
            <View style={styles.verdictCol}>
              <Text style={[styles.verdict, { color: VERDICT_COLOR[feature.verdict] }]}>
                {VERDICT_LABEL[feature.verdict] ?? feature.verdict}
              </Text>
            </View>
          </View>
        ))}
      </Card>
      {!reliable ? (
        <Text style={styles.caveat}>
          Pose quality was low for this clip - treat these numbers as provisional.
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: "row",
    paddingHorizontal: space.md,
    paddingTop: space.md,
    paddingBottom: space.sm,
  },
  headerCell: { ...type.label, color: color.inkFaint },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderTopWidth: 1,
    borderTopColor: color.line,
  },
  lastRow: { paddingBottom: space.md },
  cell: { ...type.small, color: color.ink },
  featureCol: { flex: 1.6 },
  featureLabel: { ...type.smallMedium },
  valueCol: { flex: 1, textAlign: "right" },
  referenceValue: { color: color.inkMuted },
  verdictCol: { flex: 1.3, alignItems: "flex-end" },
  verdict: { ...type.small, fontFamily: type.smallMedium.fontFamily },
  caveat: { ...type.small, color: color.softFault, marginTop: space.sm },
});
