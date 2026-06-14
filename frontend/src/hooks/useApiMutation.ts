/**
 * useApiMutation — TanStack Query mutation wrapper with
 * automatic Indonesian error handling.
 *
 * T8.5+++++++ Group 1: this is the "outbound error handling"
 * primitive. Any mutation in the app can use this wrapper
 * and get:
 * - Automatic toast.error(formatApiError(error)) on failure
 * - Optional success toast
 * - Full type safety (the mutationFn determines input/output
 *   types, so callers get autocompletion)
 *
 * Pattern:
 *   const login = useApiMutation({
 *     mutationFn: (payload: LoginPayload) => authApi.login(payload),
 *     successMessage: t.auth.welcomeBack,
 *     onSuccess: (data) => { setAuth(data); },
 *   });
 *
 *   const handleSubmit = async () => {
 *     // No try/catch needed — wrapper handles it.
 *     await login.mutateAsync({ email, password });
 *     // If we reach here, success toast already shown.
 *   };
 *
 * For flows that need custom error handling (e.g. field-level
 * errors), bypass the wrapper and use plain useMutation.
 */
import { useMutation, type UseMutationOptions } from "@tanstack/react-query";
import { toast } from "react-hot-toast";

import { formatApiError } from "@/lib/formatError";

export interface UseApiMutationOptions<TData, TError, TVariables, TContext>
  extends Omit<
    UseMutationOptions<TData, TError, TVariables, TContext>,
    "onError" | "mutationFn"
  > {
  mutationFn: (variables: TVariables) => Promise<TData>;
  /**
   * Optional toast message to show on success.
   * If not provided, no success toast is shown.
   */
  successMessage?: string;
  /**
   * Custom error handler. If provided, the default
   * formatApiError toast is NOT shown — caller is
   * responsible for displaying the error.
   * Use for field-level errors, silent failures, etc.
   */
  onError?: (error: TError) => void;
}

export function useApiMutation<TData = unknown, TError = Error, TVariables = void, TContext = unknown>(
  options: UseApiMutationOptions<TData, TError, TVariables, TContext>,
) {
  const { successMessage, onError: customOnError, ...rest } = options;
  return useMutation<TData, TError, TVariables, TContext>({
    ...rest,
    mutationFn: options.mutationFn,
    onSuccess: (data, variables, context) => {
      if (successMessage) {
        toast.success(successMessage);
      }
      // Call user's onSuccess if provided
      const userOnSuccess = (options as { onSuccess?: (data: TData, variables: TVariables, context: TContext | undefined) => void }).onSuccess;
      userOnSuccess?.(data, variables, context);
    },
    onError: (error) => {
      if (customOnError) {
        customOnError(error);
      } else {
        toast.error(formatApiError(error));
      }
    },
  });
}
