import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { AthleteComparison } from "@/api/types";
import { Card, SectionLabel } from "@/components/Primitives";
import { color, space, type } from "@/theme/tokens";

const LEVEL_LABEL: Record<string, string> = {
  BEGINNER: "Beginner range",
  DEVELOPING: "Developing",
  INTERMEDIATE: "Intermediate",
  ADVANCED: "Advanced",
  ELITE_REFERENCE_LIKE: "Professional-reference-like",
};

// Wording rule (non-negotiable): this component may say "similarity to a
// reference profile" and may say "estimated level". It must NEVER produce a
// sentence of the shape "you are X% as good as <name>", and must never call
// a level "certified" or a profile "validated" unless isValidated is true -
// which nothing in this app currently is. See backend
// docs/TECHNIQUE_METHODOLOGY.md for why.
export function AthleteComparisonCard({ comparison }: { comparison: AthleteComparison }) {
  return (
    <View>
      <SectionLabel>REFERENCE COMPARISON</SectionLabel>
      <Card style={{ gap: space.md }}>
        <View style={styles.headerRow}>
          <View>
            <Text style={styles.label}>CLOSEST REFERENCE PROFILE</Text>
            <Text style={styles.name}>{comparison.referenceDisplayName}</Text>
          </View>
          <View style={styles.similarityWrap}>
            <Text style={styles.similarity}>{Math.round(comparison.similarity)}%</Text>
            <Text style={styles.similarityLabel}>similarity</Text>
          </View>
        </View>

        <View style={styles.levelRow}>
          <Text style={styles.levelLabel}>ESTIMATED LEVEL</Text>
          <Text style={styles.levelValue}>
            {LEVEL_LABEL[comparison.levelEstimate] ?? comparison.levelEstimate}
          </Text>
        </View>
        <Text style={styles.description}>{comparison.levelDescription}</Text>

        <Text style={styles.basis}>{comparison.comparisonBasis}</Text>

        {!comparison.isValidated ? (
          <Text style={styles.disclaimer}>
            Reference profiles are hand-authored target angles, not measured data from the
            named athlete.
          </Text>
        ) : null}

        {comparison.allMatches.length > 1 ? (
          <View style={styles.otherMatches}>
            {comparison.allMatches.slice(1).map((match) => (
              <View key={match.profileId} style={styles.otherRow}>
                <Text style={styles.otherName}>{match.displayName}</Text>
                <Text style={styles.otherSimilarity}>{Math.round(match.similarity)}%</Text>
              </View>
            ))}
          </View>
        ) : null}
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" },
  label: { ...type.label, color: color.inkFaint, marginBottom: 2 },
  name: { ...type.h3, color: color.ink },
  similarityWrap: { alignItems: "flex-end" },
  similarity: { ...type.h2, color: color.accent },
  similarityLabel: { ...type.small, color: color.inkFaint },
  levelRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  levelLabel: { ...type.label, color: color.inkFaint },
  levelValue: { ...type.bodyMedium, color: color.ink },
  description: { ...type.small, color: color.inkMuted },
  basis: { ...type.small, color: color.inkMuted, fontStyle: "italic" },
  disclaimer: { ...type.small, color: color.inkFaint },
  otherMatches: { borderTopWidth: 1, borderTopColor: color.line, paddingTop: space.sm, gap: 4 },
  otherRow: { flexDirection: "row", justifyContent: "space-between" },
  otherName: { ...type.small, color: color.inkMuted },
  otherSimilarity: { ...type.smallMedium, color: color.inkMuted },
});
