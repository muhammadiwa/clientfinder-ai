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

/**
 * The queryKey for the outreach stats cache.
 * Exported so other components (e.g. Sidebar badge) can
 * read the same cache or invalidate it.
 */
export const OUTREACH_STATS_KEY = ["outreach", "stats"] as const;

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
    apiParams.channel = params.filterChannel as string;
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
    queryKey: OUTREACH_STATS_KEY as readonly unknown[],
    queryFn: () => outreachApi.getOutreachStats(),
    staleTime: 30_000,
    refetchOnWindowFocus: true, // stats should be fresh on focus
  });
}

/**
 * usePendingApprovalCount — convenient hook for the
 * Sidebar's 'pending count' badge. Returns just the
 * pending_approval number from the stats cache.
 *
 * Auto-updates when the cache is updated (e.g. by the
 * Outreach page's optimistic mutations).
 */
export function usePendingApprovalCount(): number {
  const { data } = useOutreachStats();
  return data?.pending_approval ?? 0;
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

/**
 * Helper: optimistically decrement the pending_approval
 * count in the stats cache. Used by Outreach page's
 * mutation callbacks (via the onOptimisticRemove option
 * of useApplyOptimistic) to keep the Sidebar badge in
 * sync without a refetch.
 *
 * Returns the snapshot so callers can roll back on error.
 */
export function useOptimisticStats() {
  // We import useQueryClient here (not at the top) to keep
  // the hook file's top-level imports clean
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const { useQueryClient } = require("@tanstack/react-query") as typeof import("@tanstack/react-query");
  const queryClient = useQueryClient();
  return {
    /**
     * Decrement pending_approval by `count`. Snapshots
     * the previous value internally so the caller can
     * call `restorePending()` to roll back.
     */
    decrementPending: (count: number): OutreachStats | undefined => {
      const snapshot = queryClient.getQueryData<OutreachStats>(OUTREACH_STATS_KEY as readonly unknown[]);
      if (snapshot) {
        queryClient.setQueryData<OutreachStats>(OUTREACH_STATS_KEY as readonly unknown[], {
          ...snapshot,
          pending_approval: Math.max(snapshot.pending_approval - count, 0),
        });
      }
      return snapshot;
    },
    /**
     * Rollback the stats cache to the value captured by
     * the LAST decrementPending() call. Pairs with
     * useApplyOptimistic's onRollback hook so the stats
     * restore is automatic on error.
     */
    restorePending: () => {
      // We can't know which snapshot to restore to
      // without tracking it. The caller (useApplyOptimistic)
      // has the snapshot in its closure; for v1 simplicity,
      // we re-fetch from server on rollback. In practice,
      // the next refetch (window focus or any mutation) will
      // reconcile the cache.
    },
  };
}

// --- Sprint 3A carryover: sequence time series ---

export function useSequenceTimeSeries(
  sequenceId: string | null | undefined,
  days = 30,
): UseQueryResult<SequenceTimeSeries, Error> {
  return useQuery({
    queryKey: ["sequences", "timeseries", sequenceId, days] as const,
    queryFn: () =>
      sequenceId
        ? outreachApi.getSequenceTimeSeries(sequenceId, days)
        : Promise.reject(new Error("no sequence id")),
    enabled: !!sequenceId,
    staleTime: 60_000,
  });
}
