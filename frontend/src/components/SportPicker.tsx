import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SportSupportInfo, SportType } from "@/api/types";
import { color, radius, space, type } from "@/theme/tokens";
import { SPORT_OPTIONS } from "@/utils/sportMeta";

// Renders the standard sport chip row, augmented with a COMING SOON badge
// once /sports has loaded. Before that response arrives, or if it fails,
// every chip renders exactly as before this change - failure to fetch
// support status must never block sport selection.
export function SportPicker({
  value,
  onChange,
  support,
}: {
  value: SportType;
  onChange: (sport: SportType) => void;
  support: SportSupportInfo[] | null;
}) {
  const statusFor = (sport: SportType) => support?.find((s) => s.sportType === sport)?.status;

  return (
    <View style={styles.row}>
      {SPORT_OPTIONS.map((opt) => {
        const active = value === opt.value;
        const isPreview = statusFor(opt.value) === "PREVIEW";
        return (
          <Pressable
            key={opt.value}
            onPress={() => onChange(opt.value)}
            style={[styles.chip, active && styles.chipActive]}
          >
            <Text style={[styles.chipText, active && styles.chipTextActive]}>{opt.label}</Text>
            {isPreview ? (
              <View style={[styles.badge, active && styles.badgeActive]}>
                <Text style={[styles.badgeText, active && styles.badgeTextActive]}>SOON</Text>
              </View>
            ) : null}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    borderWidth: 1,
    borderColor: color.line,
    borderRadius: radius.pill,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
  },
  chipActive: { backgroundColor: color.accent, borderColor: color.accent },
  chipText: { ...type.smallMedium, color: color.inkMuted },
  chipTextActive: { color: color.accentInk },
  badge: {
    backgroundColor: color.bgElevated2,
    borderRadius: radius.pill,
    paddingHorizontal: 6,
    paddingVertical: 1,
  },
  badgeActive: { backgroundColor: color.accentInk },
  badgeText: { fontSize: 9, letterSpacing: 0.6, color: color.inkFaint, fontWeight: "700" as const },
  badgeTextActive: { color: color.accent },
});
