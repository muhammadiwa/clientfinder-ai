import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-hot-toast";

import * as authApi from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import { useApiMutation } from "@/hooks/useApiMutation";
import { formatApiError } from "@/lib/formatError";
import { getT } from "@/i18n/id";
import type { LoginPayload } from "@/api/auth";
import type { User } from "@/types";

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);
  const queryClient = useQueryClient();

  return useApiMutation({
    mutationFn: (payload: LoginPayload) => authApi.login(payload),
    successMessage: getT().auth.welcomeBack,
    onSuccess: (data) => {
      const user: User = {
        id: data.user_id,
        email: data.email,
        role: "owner",
      };
      setAuth({
        accessToken: data.access_token,
        refreshToken: data.refresh_token,
        user,
      });
      queryClient.setQueryData(["me"], user);
    },
  });
}

export function useRegister() {
  // Returns the raw mutation so Register can show its own
  // "navigate to /login" success behavior.
  // Errors auto-toast via useApiMutation.
  return useApiMutation({
    mutationFn: authApi.register,
  });
}

export function useLogout() {
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      toast.success(getT().auth.signedOut);
    },
    onError: (error) => {
      // Logout failure is non-fatal — show a warning but
      // still clear local state. The server may have
      // already invalidated the token.
      toast.error(formatApiError(error));
    },
    onSettled: () => {
      clearAuth();
      queryClient.clear();
    },
  });
}

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["me"],
    queryFn: authApi.fetchMe,
    enabled,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
