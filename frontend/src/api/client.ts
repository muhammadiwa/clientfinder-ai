import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

import { useAuthStore } from "@/stores/auth";

const API_BASE_URL = "/api/v1";

/**
 * Shared Axios instance for all API calls.
 * - Auto-attaches Bearer token from auth store
 * - On 401: tries refresh token once, then logs out
 */
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

let isRefreshing = false;
let refreshSubscribers: Array<(token: string | null) => void> = [];

function onRefreshed(token: string | null) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

function addRefreshSubscriber(cb: (token: string | null) => void) {
  refreshSubscribers.push(cb);
}

async function tryRefresh(): Promise<string | null> {
  const { refreshToken, setAuth, clearAuth, user } = useAuthStore.getState();
  if (!refreshToken) return null;

  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    setAuth({
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
      user: user!,
    });
    return data.access_token;
  } catch {
    clearAuth();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !original._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          addRefreshSubscriber((token) => {
            if (token) {
              original._retry = true;
              original.headers.set("Authorization", `Bearer ${token}`);
              resolve(api(original));
            } else {
              reject(error);
            }
          });
        });
      }

      original._retry = true;
      isRefreshing = true;
      const newToken = await tryRefresh();
      isRefreshing = false;
      onRefreshed(newToken);

      if (newToken) {
        original.headers.set("Authorization", `Bearer ${newToken}`);
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export function isApiError(error: unknown): error is AxiosError<{ detail?: string | unknown[] }> {
  return axios.isAxiosError(error);
}
