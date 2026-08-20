import React from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { color, radius, space, type } from "@/theme/tokens";

export function Screen({
  children,
  scroll = true,
  padded = true,
}: {
  children: React.ReactNode;
  scroll?: boolean;
  padded?: boolean;
}) {
  const Container = scroll ? ScrollView : View;
  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Container
        style={styles.flex}
        contentContainerStyle={padded ? styles.padded : undefined}
        showsVerticalScrollIndicator={false}
      >
        {children}
      </Container>
    </SafeAreaView>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: object }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return <Text style={styles.sectionLabel}>{children}</Text>;
}

export function PrimaryButton({
  label,
  onPress,
  loading,
  disabled,
}: {
  label: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.primaryBtn,
        (disabled || loading) && styles.btnDisabled,
        pressed && !disabled && !loading && styles.btnPressed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={color.accentInk} />
      ) : (
        <Text style={styles.primaryBtnText}>{label}</Text>
      )}
    </Pressable>
  );
}

export function SecondaryButton({
  label,
  onPress,
  disabled,
}: {
  label: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.secondaryBtn,
        disabled && styles.btnDisabled,
        pressed && !disabled && styles.btnPressed,
      ]}
    >
      <Text style={styles.secondaryBtnText}>{label}</Text>
    </Pressable>
  );
}

export function FieldLabel({ children }: { children: string }) {
  return <Text style={styles.fieldLabel}>{children}</Text>;
}

export function TextField(props: TextInputProps) {
  return (
    <TextInput
      placeholderTextColor={color.inkFaint}
      style={styles.input}
      {...props}
    />
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.bg },
  flex: { flex: 1 },
  padded: { padding: space.lg, paddingBottom: space.xxl, gap: space.lg },
  card: {
    backgroundColor: color.bgElevated,
    borderRadius: radius.lg,
    padding: space.lg,
    gap: space.sm,
  },
  sectionLabel: { ...type.label, color: color.inkFaint, marginBottom: space.xs },
  primaryBtn: {
    backgroundColor: color.accent,
    borderRadius: radius.md,
    paddingVertical: space.md + 2,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryBtnText: { ...type.bodyMedium, color: color.accentInk, fontWeight: "700" as const },
  secondaryBtn: {
    backgroundColor: "transparent",
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.line,
    paddingVertical: space.md,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryBtnText: { ...type.bodyMedium, color: color.ink },
  btnPressed: { opacity: 0.85 },
  btnDisabled: { opacity: 0.5 },
  fieldLabel: { ...type.smallMedium, color: color.inkMuted },
  input: {
    backgroundColor: color.bgElevated2,
    borderRadius: radius.sm,
    paddingVertical: space.md,
    paddingHorizontal: space.md,
    color: color.ink,
    fontFamily: type.body.fontFamily,
    fontSize: type.body.fontSize,
  },
});
