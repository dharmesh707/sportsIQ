import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { SportType } from "@/api/types";
import { radius, space, type } from "@/theme/tokens";
import { getSportMeta } from "@/utils/sportMeta";

export function SportBadge({ sportType }: { sportType: SportType }) {
  const meta = getSportMeta(sportType);
  return (
    <View style={[styles.badge, { backgroundColor: meta.bg, borderColor: meta.accent }]}>
      <View style={[styles.dot, { backgroundColor: meta.accent }]} />
      <Text style={[styles.text, { color: meta.accent }]}>{meta.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingVertical: 4,
    paddingHorizontal: space.md,
  },
  dot: { width: 6, height: 6, borderRadius: 3 },
  text: { ...type.smallMedium },
});
