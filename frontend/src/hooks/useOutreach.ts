/**
 * useOutreach — TanStack Query hooks for Outreach data.
 *
 * T8.5+++++++ useQuery refactor: centralizes the Outreach
 * messages fetch in a proper TanStack query so it can
 * share the cache, auto-refetch, and integrate with
 * useApiMutation (T8.5+++++++ Group 1) for optimistic
 * cache updates.
 *
 * The queryKey encodes the filter state (tab, channel,
 * grade) so different filter combos don't collide.
 */
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import * as outreachApi from "@/api/outreach";
import type { Message, OutreachStats } from "@/types";
import type { MessageListFilters } from "@/api/outreach";
import { formatApiError } from "@/lib/formatError";
import { toast } from "react-hot-toast";

export interface UseMessagesParams {
  tab: "all" | "drafts" | "pending_approval" | "sent" | "failed";
  filterChannel: "all" | "email" | "whatsapp" | "threads";
  filterGrade: "all" | "A" | "B" | "C" | "D";
}

/**
 * useMessages — fetches the current tab's messages
 * with proper queryKey, caching, and refetch semantics.
 *
 * Replaces the manual useState + useEffect + listMessages
 * pattern in Outreach.tsx (T6.5 polish).
 *
 * Returns the same shape as before (items + total + page
 * etc.) for backward compat.
 */
export function useMessages(
  params: UseMessagesParams,
): UseQueryResult<{ items: Message[]; total: number }, Error> {
  // Build the API params from the UI state
  const apiParams: MessageListFilters = { page: 1, per_page: 50 };
  if (params.tab === "pending_approval") apiParams.status = "pending_approval";
  else if (params.tab === "drafts") apiParams.status = "draft";
  else if (params.tab === "failed") apiParams.status = "failed";
  else if (params.tab === "sent") {
    // "sent" tab includes all post-send states
    apiParams.status = "sent"; // approximate — backend doesn't support IN
  }
  if (params.filterChannel !== "all") {
    apiParams.channel = params.filterChannel as Message["channel"];
  }
  if (params.filterGrade !== "all") {
    apiParams.prospect_grade = params.filterGrade;
  }

  // Query key encodes all the filter state
  const queryKey = [
    "messages",
    params.tab,
    params.filterChannel,
    params.filterGrade,
  ] as const;

  return useQuery({
    queryKey,
    queryFn: () => outreachApi.listMessages(apiParams),
    staleTime: 30_000, // 30s — data is "fresh" for that long
    gcTime: 5 * 60_000, // 5min — keep in cache after unmount
    refetchOnWindowFocus: false,
  });
}

/**
 * useOutreachStats — fetches the 13-status counts that
 * power the hero KPI cards.
 */
export function useOutreachStats(): UseQueryResult<OutreachStats, Error> {
  return useQuery({
    queryKey: ["outreach", "stats"] as const,
    queryFn: () => outreachApi.getOutreachStats(),
    staleTime: 30_000,
    refetchOnWindowFocus: true, // stats should be fresh on focus
  });
}

/**
 * useMessagesWithErrorToast — same as useMessages but
 * auto-toasts errors via formatApiError. Use when the
 * caller doesn't need custom error handling.
 */
export function useMessagesWithErrorToast(
  params: UseMessagesParams,
  errorMessage?: string,
) {
  return useQuery({
    queryKey: [
      "messages",
      params.tab,
      params.filterChannel,
      params.filterGrade,
    ] as const,
    queryFn: () => {
      const apiParams: MessageListFilters = { page: 1, per_page: 50 };
      if (params.tab === "pending_approval") apiParams.status = "pending_approval";
      else if (params.tab === "drafts") apiParams.status = "draft";
      else if (params.tab === "failed") apiParams.status = "failed";
      else if (params.tab === "sent") apiParams.status = "sent";
      if (params.filterChannel !== "all") {
        apiParams.channel = params.filterChannel as Message["channel"];
      }
      if (params.filterGrade !== "all") {
        apiParams.prospect_grade = params.filterGrade;
      }
      return outreachApi.listMessages(apiParams);
    },
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    meta: {
      // Custom meta so callers can decide whether to toast
      errorMessage,
    },
  });
}

/**
 * Helper: imperatively show a messages error toast.
 * Use this inside a component that already has the query
 * result and wants to react to errors (e.g. effect hook).
 */
export function showMessagesErrorToast(
  error: Error,
  fallbackMessage: string,
) {
  toast.error(fallbackMessage || formatApiError(error));
}
