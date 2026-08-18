import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Trend } from "@/api/types";
import { radius, space, trendColor, trendLabel, type } from "@/theme/tokens";

const GLYPH: Record<Trend, string> = {
  improving: "▲",
  stable: "▬",
  declining: "▼",
  insufficient_data: "·",
};

export function TrendPill({ trend }: { trend: Trend }) {
  const c = trendColor[trend];
  return (
    <View style={[styles.pill, { borderColor: c }]}>
      <Text style={[styles.glyph, { color: c }]}>{GLYPH[trend]}</Text>
      <Text style={[styles.label, { color: c }]}>{trendLabel[trend]}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    alignSelf: "flex-start",
    borderWidth: 1,
    borderRadius: radius.pill,
    paddingVertical: 4,
    paddingHorizontal: space.md,
  },
  glyph: { fontSize: 10 },
  label: { ...type.smallMedium },
});
