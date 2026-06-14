/**
 * useOptimisticMessages — F4 optimistic UI for Outreach mutations.
 *
 * T8.5+++++++ Group 2 (initial): local state mutations only.
 * T8.5+++++++ (cache-level): also updates the TanStack Query
 * cache via setQueryData, so other components viewing the
 * same queryKey see the update.
 * T8.5+++++++ (race fix): cancels in-flight refetches before
 * setQueryData so they don't overwrite the optimistic update.
 * T8.5+++++++ (badge): also decrements the stats cache so
 * the Sidebar's 'pending count' badge auto-updates.
 *
 * Pattern (local + cache):
 *   1. User clicks "Approve" on a message
 *   2. We IMMEDIATELY:
 *      a. Cancel any in-flight refetch on this queryKey
 *      b. Snapshot the current query cache
 *      c. Remove the message from the cache (via setQueryData)
 *      d. Decrement the pending count in the stats cache
 *      e. Remove from local state (so the optimistic-UI
 *         helper still works for any UI bound to local state)
 *   3. We await the API call
 *   4. On success: caches are already correct; the next
 *      refetch will confirm
 *   5. On failure: we RESTORE the cache, the stats, AND
 *      local state (rollback) and show the error toast
 */
import { useCallback } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";

import type { Message } from "@/types";

/**
 * Apply an optimistic mutation to BOTH the local messages
 * state AND the TanStack query cache, with automatic
 * rollback on error.
 *
 * Usage:
 *   const applyOptimistic = useApplyOptimistic({
 *     messages, setMessages,
 *     queryKey: messagesQueryKey,
 *   });
 *   await applyOptimistic([id], async () => {
 *     await approveMessage(id, { approve: true });
 *   });
 *
 * On success: leaves both state + cache updated.
 * On throw: rolls back BOTH, re-throws for caller to toast.
 *
 * T8.5+++++++ (race fix): also calls cancelQueries before
 * setQueryData so any in-flight refetch doesn't overwrite
 * the optimistic update with stale data.
 *
 * T8.5+++++++ (badge): also decrements the stats cache
 * ('outreach', 'stats') — specifically the pending_approval
 * count. This way the Sidebar's badge auto-updates without
 * needing a refetch.
 */
export function useApplyOptimistic(opts: {
  messages: Message[];
  setMessages: (next: Message[]) => void;
  queryKey: QueryKey;
  /** Optional: called when each message is removed optimistically
   *  (used by Outreach to also decrement the stats cache
   *  for the Sidebar badge). */
  onOptimisticRemove?: (removedCount: number) => void;
  /** Optional: called on error rollback. Pairs with
   *  onOptimisticRemove so the caller can revert any
   *  external state mutations (e.g. stats cache). */
  onRollback?: () => void;
}) {
  const { messages, setMessages, queryKey, onOptimisticRemove, onRollback } = opts;
  const queryClient = useQueryClient();

  return useCallback(
    async (
      ids: string[],
      mutation: () => Promise<void>,
    ) => {
      const idSet = new Set(ids);
      if (idSet.size === 0) {
        // No-op: just run the mutation
        try {
          await mutation();
        } catch {
          throw new Error("mutation failed");
        }
        return;
      }

      // Snapshot BOTH the local state and the cache so
      // we can roll back on error.
      const localSnapshot = messages;
      const cacheSnapshot = queryClient.getQueryData<{ items: Message[]; total: number }>(queryKey);

      // T8.5+++++++ (race fix): cancel any in-flight refetch
      // on this queryKey before we mutate. Otherwise the
      // refetch could fire AFTER our setQueryData and
      // overwrite the optimistic update with stale server
      // data. The refetch is abandoned and will be re-scheduled
      // on the next invalidation.
      await queryClient.cancelQueries({ queryKey });

      // 1) Optimistic local update
      setMessages(messages.filter((m) => !idSet.has(m.id)));

      // 2) Optimistic cache update (matches the queryKey
      //    shape used by useMessages in useOutreach.ts)
      if (cacheSnapshot) {
        queryClient.setQueryData<{ items: Message[]; total: number }>(
          queryKey,
          {
            ...cacheSnapshot,
            items: cacheSnapshot.items.filter((m) => !idSet.has(m.id)),
            total: Math.max(cacheSnapshot.total - ids.length, 0),
          },
        );
      }

      // T8.5+++++++ (badge): also update the stats cache
      // so the Sidebar's pending count badge auto-updates.
      onOptimisticRemove?.(ids.length);

      try {
        await mutation();
      } catch {
        // Rollback BOTH
        setMessages(localSnapshot);
        if (cacheSnapshot !== undefined) {
          queryClient.setQueryData(queryKey, cacheSnapshot);
        }
        // Pair the stats decrement with a stats restore.
        onRollback?.();
        throw new Error("mutation failed");
      }
    },
    [messages, setMessages, queryClient, queryKey, onOptimisticRemove, onRollback],
  );
}

/**
 * Lower-level helper for advanced use cases.
 * Returns a function that takes ids and a mutation, and
 * applies the optimistic update + rollback. Useful when
 * you need to compose with other side effects.
 */
export function useOptimisticRemove() {
  const queryClient = useQueryClient();
  return useCallback(
    (queryKey: QueryKey, ids: Iterable<string>) => {
      const idSet = new Set(ids);
      if (idSet.size === 0) return undefined;
      const snapshot = queryClient.getQueryData<{ items: Message[]; total: number }>(queryKey);
      if (snapshot) {
        queryClient.setQueryData<{ items: Message[]; total: number }>(queryKey, {
          ...snapshot,
          items: snapshot.items.filter((m) => !idSet.has(m.id)),
          total: Math.max(snapshot.total - idSet.size, 0),
        });
      }
      return snapshot; // caller can call setQueryData(queryKey, snapshot) to rollback
    },
    [queryClient],
  );
}

