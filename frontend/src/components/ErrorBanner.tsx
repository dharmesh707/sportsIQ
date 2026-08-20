import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { color, radius, space, type } from "@/theme/tokens";

interface Props {
  message: string;
  onRetry?: () => void;
}

// Every screen that calls the API routes failures here. The contract
// guarantees { error: { code, message } } from every endpoint (Section 3),
// so this is the one place that turns that into UI — no per-screen error copy.
export function ErrorBanner({ message, onRetry }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.text}>{message}</Text>
      {onRetry ? (
        <Pressable onPress={onRetry} style={styles.retryBtn} hitSlop={8}>
          <Text style={styles.retryText}>Try again</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: color.hardFaultBg,
    borderRadius: radius.md,
    padding: space.lg,
    gap: space.sm,
  },
  text: { ...type.body, color: color.ink },
  retryBtn: {
    alignSelf: "flex-start",
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
    borderRadius: radius.sm,
    backgroundColor: color.hardFault,
  },
  retryText: { ...type.smallMedium, color: color.bg },
});
