import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { color, space, type } from "@/theme/tokens";

interface Props {
  title: string;
  body: string;
  action?: React.ReactNode;
}

// Empty states are an invitation to act, not an error screen (Sections 3, 4
// of the contract: zero sessions still returns 200 with zeroed/empty fields).
export function EmptyState({ title, body, action }: Props) {
  return (
    <View style={styles.wrap}>
      <View style={styles.mark} />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
      {action}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    alignItems: "center",
    paddingVertical: space.xxl,
    paddingHorizontal: space.xl,
    gap: space.sm,
  },
  mark: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: color.accent,
    marginBottom: space.sm,
  },
  title: { ...type.h3, color: color.ink, textAlign: "center" },
  body: { ...type.body, color: color.inkMuted, textAlign: "center" },
});
