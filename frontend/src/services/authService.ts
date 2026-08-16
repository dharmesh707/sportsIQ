import * as SecureStore from 'expo-secure-store';
import { apiClient } from '../api/client';
import { AuthResponse, User } from '../types/api';

export async function register(email: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/register', { email, password });
  await SecureStore.setItemAsync('accessToken', data.accessToken);
  return data;
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await apiClient.post<AuthResponse>('/auth/login', { email, password });
  await SecureStore.setItemAsync('accessToken', data.accessToken);
  return data;
}

export async function logout(): Promise<void> {
  await SecureStore.deleteItemAsync('accessToken');
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<{ user: User }>('/auth/me');
  return data.user;
}
