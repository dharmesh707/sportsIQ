import React, { useState } from "react";
import { Text, View, StyleSheet } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { AuthStackParamList } from "@/navigation/types";
import { Screen, PrimaryButton, SecondaryButton, FieldLabel, TextField } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { useAuth } from "@/context/AuthContext";
import { color, space, type } from "@/theme/tokens";

type Props = NativeStackScreenProps<AuthStackParamList, "Login">;

export default function LoginScreen({ navigation }: Props) {
  const { login, error, clearError } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = email.trim().length > 3 && password.length >= 6;

  const onSubmit = async () => {
    clearError();
    setSubmitting(true);
    try {
      await login(email.trim(), password);
    } catch {
      // error surfaced via context.error
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.wordmark}>SportsIQ</Text>
        <Text style={styles.tagline}>Your form, measured against itself.</Text>
      </View>

      {error ? <ErrorBanner message={error} /> : null}

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
            placeholder="••••••••"
            autoComplete="password"
          />
        </View>
        <PrimaryButton label="Sign in" onPress={onSubmit} loading={submitting} disabled={!canSubmit} />
        <SecondaryButton label="Create an account" onPress={() => navigation.navigate("Register")} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: "center", marginTop: space.xxl, marginBottom: space.xl, gap: 6 },
  wordmark: { ...type.h1, color: color.ink },
  tagline: { ...type.body, color: color.inkMuted },
  form: { gap: space.lg },
  field: { gap: space.xs },
});
