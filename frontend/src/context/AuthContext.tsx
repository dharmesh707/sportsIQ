import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import * as SecureStore from "expo-secure-store";
import { api, configureApiClient } from "@/api/client";
import { ApiError, User } from "@/api/types";

const TOKEN_KEY = "sportsiq_access_token";

interface AuthContextValue {
  status: "loading" | "signedOut" | "signedIn";
  user: User | null;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<"loading" | "signedOut" | "signedIn">("loading");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);
  const tokenRef = useRef<string | null>(null);

  const clearAuthState = useCallback(() => {
    tokenRef.current = null;
    setUser(null);
    setStatus("signedOut");
  }, []);

  // Single 401 handler for the whole app (build brief non-negotiable #5).
  useEffect(() => {
    configureApiClient({
      getToken: () => tokenRef.current,
      onUnauthorized: () => {
        SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => {});
        clearAuthState();
      },
    });
  }, [clearAuthState]);

  // Bootstrap from persisted token on cold start.
  useEffect(() => {
    (async () => {
      try {
        const saved = await SecureStore.getItemAsync(TOKEN_KEY);
        if (!saved) {
          setStatus("signedOut");
          return;
        }
        tokenRef.current = saved;
        const { user: me } = await api.me();
        setUser(me);
        setStatus("signedIn");
      } catch {
        await SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => {});
        clearAuthState();
      }
    })();
  }, [clearAuthState]);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const res = await api.login(email, password);
      tokenRef.current = res.accessToken;
      await SecureStore.setItemAsync(TOKEN_KEY, res.accessToken);
      setUser(res.user);
      setStatus("signedIn");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't sign in.");
      throw e;
    }
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const res = await api.register(email, password);
      tokenRef.current = res.accessToken;
      await SecureStore.setItemAsync(TOKEN_KEY, res.accessToken);
      setUser(res.user);
      setStatus("signedIn");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't create your account.");
      throw e;
    }
  }, []);

  const logout = useCallback(async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY).catch(() => {});
    clearAuthState();
  }, [clearAuthState]);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{ status, user, error, login, register, logout, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
