import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { PoseQualityInfo } from "@/api/types";
import { color, radius, space, type } from "@/theme/tokens";

// Uses the SAME semantic colors as FaultCard's hard/soft distinction so the
// whole result screen speaks one visual language for "how much to trust
// this" - HIGH/MEDIUM read as positive/neutral, LOW reads like a soft fault
// (flagged, not an error), matching Freedom-to-Play's non-punitive tone.
const BAND_COLOR: Record<string, string> = {
  HIGH: color.positive,
  MEDIUM: color.softFault,
  LOW: color.hardFault,
  REJECT: color.hardFault,
};

const BAND_LABEL: Record<string, string> = {
  HIGH: "HIGH",
  MEDIUM: "MEDIUM",
  LOW: "LOW",
  REJECT: "TOO LOW",
};

export function PoseQualityBadge({ quality }: { quality: PoseQualityInfo }) {
  const accent = BAND_COLOR[quality.band] ?? color.inkFaint;
  return (
    <View style={styles.wrap}>
      <View style={styles.headerRow}>
        <Text style={styles.title}>POSE QUALITY</Text>
        <View style={[styles.pill, { borderColor: accent }]}>
          <Text style={[styles.pillText, { color: accent }]}>
            {quality.detectionPercent.toFixed(0)}% \u2014 {BAND_LABEL[quality.band] ?? quality.band}
          </Text>
        </View>
      </View>
      <Text style={styles.detail}>
        Tracked in {quality.detectedFrames} of {quality.totalFrames} frames
      </Text>
      {!quality.isReliable ? <Text style={styles.caveat}>{quality.message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: color.bgElevated,
    borderRadius: radius.md,
    padding: space.md,
    gap: 6,
  },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  title: { ...type.label, color: color.inkFaint },
  pill: {
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingVertical: 3,
    paddingHorizontal: space.sm,
  },
  pillText: { ...type.smallMedium },
  detail: { ...type.small, color: color.inkMuted },
  caveat: { ...type.small, color: color.softFault, marginTop: 2 },
});
