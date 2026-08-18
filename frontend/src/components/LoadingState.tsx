import React from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { color, space, type } from "@/theme/tokens";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <View style={styles.wrap}>
      <ActivityIndicator color={color.accent} size="large" />
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { alignItems: "center", justifyContent: "center", paddingVertical: space.xxl, gap: space.md },
  label: { ...type.small, color: color.inkMuted },
});
