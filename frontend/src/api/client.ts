import axios, { AxiosError } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { ApiError } from '../types/api';

/**
 * Point this at Dharmesh's running backend. Local dev over wifi: use his
 * machine's LAN IP, not localhost (localhost on your phone means the phone
 * itself, not his laptop). Once deployed: the Railway URL.
 * TODO: move to an env var (EXPO_PUBLIC_API_URL) once that's decided as a
 * team — hardcoded here only so Day 1 scaffolding has something to build against.
 */
export const API_BASE_URL = 'http://REPLACE_WITH_BACKEND_HOST:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
});

// Attach JWT automatically, per the brief's auth UX: token lives in
// expo-secure-store, injected only when present (most screens are
// browsable logged out — see brief section 4).
apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Normalizes every failure to the contract's exact error shape
 * ({ code, message }), so callers never have to guess whether they got a
 * network error, a validation error, or a 500 — they always get ApiError.
 */
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error: ApiError }>) => {
    if (error.response?.data?.error) {
      return Promise.reject(error.response.data.error);
    }
    // Network failure, timeout, or a response that somehow doesn't match
    // the contract shape (backend bug) — still normalize to ApiError so
    // calling code has one shape to handle, always.
    const fallback: ApiError = {
      code: 'network_error',
      message: 'Could not reach the server. Check your connection and try again.',
    };
    return Promise.reject(fallback);
  }
);
