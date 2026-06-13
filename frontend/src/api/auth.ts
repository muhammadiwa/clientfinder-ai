import { api } from "./client";
import { useAuthStore } from "@/stores/auth";
import type { User } from "@/types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", payload);

  // Fetch user info to populate auth store
  const user: User = {
    id: data.user_id,
    email: data.email,
    role: "owner", // backend defaults first user to owner
  };

  useAuthStore.getState().setAuth({
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    user,
  });

  return data;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name?: string;
}): Promise<User> {
  const { data } = await api.post<User>("/auth/register", payload);
  return data;
}

export async function logout(): Promise<void> {
  const { refreshToken, clearAuth } = useAuthStore.getState();
  try {
    if (refreshToken) {
      await api.post("/auth/logout", { refresh_token: refreshToken });
    }
  } catch {
    // ignore — clear local state anyway
  }
  clearAuth();
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}
