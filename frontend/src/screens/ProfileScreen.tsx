import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Screen, Card, SecondaryButton } from "@/components/Primitives";
import { useAuth } from "@/context/AuthContext";
import { color, space, type } from "@/theme/tokens";
import { formatDateTime } from "@/utils/format";

export default function ProfileScreen() {
  const { user, logout } = useAuth();

  return (
    <Screen>
      <Text style={styles.title}>Profile</Text>

      <Card style={styles.card}>
        <View style={styles.avatar}>
          <Text style={styles.avatarInitial}>
            {user?.email?.charAt(0).toUpperCase() ?? "?"}
          </Text>
        </View>
        <Text style={styles.email}>{user?.email ?? "—"}</Text>
        {user?.createdAt ? (
          <Text style={styles.meta}>Member since {formatDateTime(user.createdAt)}</Text>
        ) : null}
      </Card>

      <SecondaryButton label="Log out" onPress={logout} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...type.h1, color: color.ink },
  card: { alignItems: "center", gap: space.sm, paddingVertical: space.xl },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: color.accent,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: space.sm,
  },
  avatarInitial: { ...type.h1, color: color.accentInk },
  email: { ...type.h3, color: color.ink },
  meta: { ...type.small, color: color.inkFaint },
});
