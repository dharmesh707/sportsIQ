import React from "react";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { Text } from "react-native";
import { useAuth } from "@/context/AuthContext";
import { color } from "@/theme/tokens";
import { LoadingState } from "@/components/LoadingState";

import LoginScreen from "@/screens/auth/LoginScreen";
import RegisterScreen from "@/screens/auth/RegisterScreen";
import DashboardScreen from "@/screens/DashboardScreen";
import AnalyzeScreen from "@/screens/AnalyzeScreen";
import HistoryScreen from "@/screens/HistoryScreen";
import ProgressScreen from "@/screens/ProgressScreen";
import TrainScreen from "@/screens/TrainScreen";
import ProfileScreen from "@/screens/ProfileScreen";
import AnalysisDetailScreen from "@/screens/AnalysisDetailScreen";

const AuthStack = createNativeStackNavigator();
const RootStack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const TAB_ICON: Record<string, string> = {
  DashboardTab: "▦",
  AnalyzeTab: "◎",
  HistoryTab: "≡",
  ProgressTab: "↗",
  TrainTab: "✦",
  ProfileTab: "◐",
};

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: color.accent,
        tabBarInactiveTintColor: color.inkFaint,
        tabBarStyle: {
          backgroundColor: color.bgElevated,
          borderTopColor: color.line,
          height: 64,
          paddingBottom: 10,
          paddingTop: 8,
        },
        tabBarLabelStyle: { fontSize: 10, fontFamily: "Inter_500Medium" },
        tabBarIcon: () => (
          <Text style={{ fontSize: 18, color: color.inkFaint }}>{TAB_ICON[route.name]}</Text>
        ),
      })}
    >
      <Tab.Screen name="DashboardTab" component={DashboardScreen} options={{ title: "Dashboard" }} />
      <Tab.Screen name="AnalyzeTab" component={AnalyzeScreen} options={{ title: "Analyze" }} />
      <Tab.Screen name="HistoryTab" component={HistoryScreen} options={{ title: "History" }} />
      <Tab.Screen name="ProgressTab" component={ProgressScreen} options={{ title: "Progress" }} />
      <Tab.Screen name="TrainTab" component={TrainScreen} options={{ title: "Train" }} />
      <Tab.Screen name="ProfileTab" component={ProfileScreen} options={{ title: "Profile" }} />
    </Tab.Navigator>
  );
}

function AuthNavigator() {
  return (
    <AuthStack.Navigator screenOptions={{ headerShown: false }}>
      <AuthStack.Screen name="Login" component={LoginScreen} />
      <AuthStack.Screen name="Register" component={RegisterScreen} />
    </AuthStack.Navigator>
  );
}

const navTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: color.bg,
    card: color.bgElevated,
    text: color.ink,
    border: color.line,
    primary: color.accent,
  },
};

export function RootNavigator() {
  const { status } = useAuth();

  if (status === "loading") {
    return <LoadingState label="Warming up…" />;
  }

  return (
    <NavigationContainer theme={navTheme}>
      {status === "signedOut" ? (
        <AuthNavigator />
      ) : (
        <RootStack.Navigator screenOptions={{ headerShown: false }}>
          <RootStack.Screen name="Main" component={MainTabs} />
          <RootStack.Screen
            name="AnalysisDetail"
            component={AnalysisDetailScreen}
            options={{
              headerShown: true,
              title: "Session",
              headerStyle: { backgroundColor: color.bg },
              headerTintColor: color.ink,
              headerShadowVisible: false,
            }}
          />
        </RootStack.Navigator>
      )}
    </NavigationContainer>
  );
}
