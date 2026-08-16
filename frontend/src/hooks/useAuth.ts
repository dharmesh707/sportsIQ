import { useState, useCallback } from 'react';
import * as authService from '../services/authService';
import { User, ApiError } from '../types/api';

/**
 * Example of the brief's Screen -> Hook -> Service -> Axios flow. A screen
 * should only ever import this hook, never authService or apiClient
 * directly. This is the pattern to copy for useAnalyze, useNutrition, etc.
 */
export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const doLogin = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const { user } = await authService.login(email, password);
      setUser(user);
      return user;
    } catch (err) {
      setError(err as ApiError);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const doRegister = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const { user } = await authService.register(email, password);
      setUser(user);
      return user;
    } catch (err) {
      setError(err as ApiError);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const doLogout = useCallback(async () => {
    await authService.logout();
    setUser(null);
  }, []);

  return { user, loading, error, login: doLogin, register: doRegister, logout: doLogout };
}
