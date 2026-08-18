import React, { useState } from "react";
import { Text, View, StyleSheet } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { AuthStackParamList } from "@/navigation/types";
import { Screen, PrimaryButton, SecondaryButton, FieldLabel, TextField } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { useAuth } from "@/context/AuthContext";
import { color, space, type } from "@/theme/tokens";

type Props = NativeStackScreenProps<AuthStackParamList, "Register">;

export default function RegisterScreen({ navigation }: Props) {
  const { register, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const mismatch = confirm.length > 0 && confirm !== password;
  // Matches backend RegisterRequest validation exactly (app/schemas/auth.py):
  // 8+ chars, mixed case, at least one digit. Keep in sync if that changes.
  const passwordStrongEnough =
    password.length >= 8 &&
    /[a-z]/.test(password) &&
    /[A-Z]/.test(password) &&
    /\d/.test(password);
  const canSubmit = email.trim().length > 3 && passwordStrongEnough && !mismatch;

  const onSubmit = async () => {
    clearError();
    setSubmitting(true);
    try {
      await register(email.trim(), password);
    } catch {
      // error surfaced via context.error
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.wordmark}>Create account</Text>
        <Text style={styles.tagline}>One profile, every sport you train.</Text>
      </View>

      {error ? <ErrorBanner message={error} /> : null}
      {mismatch ? <ErrorBanner message="Passwords don't match." /> : null}

      <View style={styles.form}>
        <View style={styles.field}>
          <FieldLabel>Email</FieldLabel>
          <TextField
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="you@example.com"
            autoComplete="email"
          />
        </View>
        <View style={styles.field}>
          <FieldLabel>Password</FieldLabel>
          <TextField
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            placeholder="8+ chars, upper & lowercase, a number"
            autoComplete="password-new"
          />
        </View>
        <View style={styles.field}>
          <FieldLabel>Confirm password</FieldLabel>
          <TextField
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry
            placeholder="••••••••"
          />
        </View>
        <PrimaryButton label="Create account" onPress={onSubmit} loading={submitting} disabled={!canSubmit} />
        <SecondaryButton label="I already have an account" onPress={() => navigation.navigate("Login")} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: "center", marginTop: space.xxl, marginBottom: space.xl, gap: 6 },
  wordmark: { ...type.h1, color: color.ink, textAlign: "center" },
  tagline: { ...type.body, color: color.inkMuted, textAlign: "center" },
  form: { gap: space.lg },
  field: { gap: space.xs },
});
